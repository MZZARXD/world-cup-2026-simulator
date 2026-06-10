import random
import time

# ============================================================
# HOW THIS SIMULATOR WORKS (READ THIS FIRST!)
# ============================================================
# 1. Each team gets an attack and defense rating based on its FIFA rank.
# 2. Group stage: every team plays the other three in its group.
#    Goals are calculated using team ratings + randomness.
# 3. Top 2 from each group advance, plus the 8 best 3rd‑place teams.
# 4. Knockout rounds: single elimination. Tied matches go to extra time,
#    then penalty shootout.
# 5. If a much lower‑ranked team wins, it's logged as a "giant killing".
# 6. After the final, the team with the most goals gets the "Highest Scoring Team" award.
# ============================================================

# ============================================================
# CONSTANTS (easy to adjust)
# ============================================================
GIANT_KILL_RANK_DIFFERENCE = 25   # Underdog wins if ranked 25+ places worse
RATING_MIN = 68
RATING_MAX = 96
RATING_BASE_START = 96
RATING_RANK_FACTOR = 0.35

# ============================================================
# TOURNAMENT DATA
# ============================================================
GROUPS = {
    "Group A": ["Mexico", "South Africa", "South Korea", "Czech Republic"],
    "Group B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    "Group C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "Group D": ["United States", "Paraguay", "Australia", "Turkey"],
    "Group E": ["Germany", "Curaçao", "Ivory Coast", "Ecuador"],
    "Group F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "Group G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "Group H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "Group I": ["France", "Senegal", "Iraq", "Norway"],
    "Group J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "Group K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "Group L": ["England", "Croatia", "Ghana", "Panama"]
}

FIFA_RANKINGS = {
    "France": 1, "Spain": 2, "Argentina": 3, "England": 4, "Portugal": 5,
    "Brazil": 6, "Netherlands": 7, "Morocco": 8, "Belgium": 9, "Germany": 10,
    "Croatia": 11, "Colombia": 13, "Senegal": 14, "Mexico": 15, "United States": 16,
    "Uruguay": 17, "Japan": 18, "Switzerland": 19, "Iran": 21, "Turkey": 22,
    "Ecuador": 23, "Austria": 24, "South Korea": 25, "Australia": 27, "Algeria": 28,
    "Egypt": 29, "Canada": 30, "Norway": 31, "Panama": 33, "Ivory Coast": 34,
    "Sweden": 38, "Paraguay": 40, "Czech Republic": 41, "Scotland": 43, "Tunisia": 44,
    "DR Congo": 46, "Uzbekistan": 50, "Qatar": 55, "Iraq": 57, "South Africa": 60,
    "Saudi Arabia": 61, "Jordan": 63, "Bosnia and Herzegovina": 65, "Cape Verde": 69,
    "Ghana": 74, "Curaçao": 82, "Haiti": 83, "New Zealand": 85
}

# Global state variables
team_ratings = {}      # each team -> {"attack": value, "defense": value}
standings = {}         # each team -> match stats
advancing_teams = []   # current knockout pool
semi_final_losers = [] # for bronze match
upsets_logged = []     # list of giant killings


# ============================================================
# SETUP: Give each team realistic attack/defense ratings
# ============================================================
def setup_ratings():
    """This is used to generate attack & defense ratings for every team based on FIFA rank."""
    global team_ratings, standings
    team_ratings.clear()
    standings.clear()

    for group_name, team_list in GROUPS.items():
        for team in team_list:
            rank = FIFA_RANKINGS.get(team, 50)   # default rank 50 if missing
            # Higher rank (smaller number) = stronger team
            raw_rating = RATING_BASE_START - int(rank * RATING_RANK_FACTOR)
            # Clamp to allowed range
            if raw_rating < RATING_MIN:
                raw_rating = RATING_MIN
            if raw_rating > RATING_MAX:
                raw_rating = RATING_MAX

            # Add randomness to make matches less predictable
            team_ratings[team] = {
                "attack": raw_rating + random.randint(-3, 3),
                "defense": raw_rating + random.randint(-3, 3)
            }

            # Initialize group stage stats for this team
            standings[team] = {
                "MP": 0,    # matches played
                "W": 0,     # wins
                "D": 0,     # draws
                "L": 0,     # losses
                "GF": 0,    # goals for
                "GA": 0,    # goals against
                "PTS": 0,   # points
                "Group": group_name
            }


# ============================================================
# MATCH SIMULATION (core logic)
# ============================================================
def calculate_goals(attacking_team, defending_team):
    """This is used to compute how many goals a team scores against another."""
    attack = team_ratings[attacking_team]["attack"]
    defense = team_ratings[defending_team]["defense"]
    raw_goals = (attack - defense) * 0.05 + random.randint(0, 3)
    goals = int(raw_goals)
    if goals < 0:
        goals = 0
    return goals


def update_standings_after_match(team_a, team_b, goals_a, goals_b):
    """This is used to update all statistics for both teams after a match."""
    # Goals and matches played
    standings[team_a]["GF"] += goals_a
    standings[team_a]["GA"] += goals_b
    standings[team_a]["MP"] += 1

    standings[team_b]["GF"] += goals_b
    standings[team_b]["GA"] += goals_a
    standings[team_b]["MP"] += 1

    # Win / Draw / Loss and points
    if goals_a > goals_b:
        standings[team_a]["W"] += 1
        standings[team_a]["PTS"] += 3
        standings[team_b]["L"] += 1
    elif goals_b > goals_a:
        standings[team_b]["W"] += 1
        standings[team_b]["PTS"] += 3
        standings[team_a]["L"] += 1
    else:  # draw
        standings[team_a]["D"] += 1
        standings[team_b]["D"] += 1
        standings[team_a]["PTS"] += 1
        standings[team_b]["PTS"] += 1


# ============================================================
# GROUP STAGE (with fixed 3rd‑place selection)
# ============================================================
def simulate_group_stage(show_live):
    """This is used to run all group matches and pick the 32 advancing teams."""
    global advancing_teams, upsets_logged

    setup_ratings()
    advancing_teams = []
    upsets_logged = []

    print(f"\n⚽ Simulating Group Stage (Live feed = {'ON' if show_live else 'OFF'})...")

    # This is used to sort teams by points, then goal difference, then goals scored
    def sort_key(team):
        return (standings[team]["PTS"],
                standings[team]["GF"] - standings[team]["GA"],
                standings[team]["GF"])

    # ----- Play every match in every group -----
    for group_name, team_list in GROUPS.items():
        if show_live:
            print(f"\n🧱 {group_name} Fixtures:")
            print("-" * 35)

        # Each pair of teams plays once
        for i in range(len(team_list)):
            for j in range(i + 1, len(team_list)):
                team_a = team_list[i]
                team_b = team_list[j]

                goals_a = calculate_goals(team_a, team_b)
                goals_b = calculate_goals(team_b, team_a)
                update_standings_after_match(team_a, team_b, goals_a, goals_b)

                if show_live:
                    print(f"   {team_a:<15}  {goals_a} - {goals_b}  {team_b}")
                    time.sleep(0.05)

    # ----- Select top 2 from each group -----
    automatic_qualifiers = []
    third_place_teams = []

    for group_name, team_list in GROUPS.items():
        sorted_teams = sorted(team_list, key=sort_key, reverse=True)
        automatic_qualifiers.append(sorted_teams[0])
        automatic_qualifiers.append(sorted_teams[1])
        third_place_teams.append(sorted_teams[2])

    # ----- Choose the best 8 third‑placed teams (using same sort key) -----
    third_place_teams.sort(key=sort_key, reverse=True)
    best_third = third_place_teams[:8]

    # ----- Build the knockout bracket and shuffle -----
    advancing_teams = automatic_qualifiers + best_third
    random.shuffle(advancing_teams)

    # ----- Save full standings to a file -----
    with open("world_cup_standings.txt", "w", encoding="utf-8") as file:
        file.write("=== FIFA WORLD CUP 2026 STANDINGS ===\n\n")
        for group_name, team_list in GROUPS.items():
            file.write(f"--- {group_name} ---\n")
            sorted_teams = sorted(team_list, key=sort_key, reverse=True)
            for team in sorted_teams:
                stats = standings[team]
                line = (f"{team:<22} MP:{stats['MP']} W:{stats['W']} D:{stats['D']} "
                        f"L:{stats['L']} GF:{stats['GF']} GA:{stats['GA']} PTS:{stats['PTS']}\n")
                file.write(line)
            file.write("\n")


# ============================================================
# KNOCKOUT MATCH (with extra time and penalties)
# ============================================================
def knockout_match(team_a, team_b, track_stats=True):
    """
    To simulate a single elimination match.
    Returns (winner, loser).
    If track_stats is True, updates goals & stats for "Highest Scoring Team" award.
    """
    # Regulation time
    goals_a = calculate_goals(team_a, team_b)
    goals_b = calculate_goals(team_b, team_a)
    if track_stats:
        update_standings_after_match(team_a, team_b, goals_a, goals_b)

    print(f"   {team_a} vs {team_b} -> {goals_a}-{goals_b}", end="")

    # Regulation winner?
    if goals_a != goals_b:
        winner = team_a if goals_a > goals_b else team_b
        loser = team_b if winner == team_a else team_a
        print(f" (Winner: {winner})")
        check_giant_kill(winner, loser)
        return winner, loser

    # Extra time (each team can score 0 or 1 extra goal)
    extra_a = random.randint(0, 1)
    extra_b = random.randint(0, 1)
    if track_stats:
        standings[team_a]["GF"] += extra_a
        standings[team_a]["GA"] += extra_b
        standings[team_b]["GF"] += extra_b
        standings[team_b]["GA"] += extra_a

    goals_a += extra_a
    goals_b += extra_b

    if goals_a != goals_b:
        winner = team_a if goals_a > goals_b else team_b
        loser = team_b if winner == team_a else team_a
        print(f" -> {goals_a}-{goals_b} after extra time! Winner: {winner}")
        check_giant_kill(winner, loser)
        return winner, loser

    # Penalty shootout (each team scores 3-5 penalties, must be different)
    while True:
        pens_a = random.randint(3, 5)
        pens_b = random.randint(3, 5)
        if pens_a != pens_b:
            break

    winner = team_a if pens_a > pens_b else team_b
    loser = team_b if winner == team_a else team_a
    print(f" -> Tied after extra time! Penalties: ({pens_a})-({pens_b}) -> {winner} wins!")
    check_giant_kill(winner, loser)
    return winner, loser


def check_giant_kill(winner, loser):
    """If winner is ranked much lower than loser, record an upset."""
    rank_winner = FIFA_RANKINGS.get(winner, 50)
    rank_loser = FIFA_RANKINGS.get(loser, 50)
    if rank_winner > rank_loser + GIANT_KILL_RANK_DIFFERENCE:
        upset = f"😱 GIANT KILLING: {winner} (Rank {rank_winner}) eliminated {loser} (Rank {rank_loser})!"
        upsets_logged.append(upset)


# ============================================================
# RUN AN ENTIRE KNOCKOUT ROUND
# ============================================================
def run_knockout_round(round_name):
    """Simulate one round (e.g., 'Round of 32') using current advancing_teams."""
    global advancing_teams, semi_final_losers

    if not advancing_teams:
        print("\n❌ No teams in knockout pool. Run the Group Stage first!")
        return False

    print(f"\n⚡🏆 Simulating: {round_name} 🏆⚡")
    print("-" * 50)
    time.sleep(0.4)

    next_round = []
    # Pair consecutive teams: (0,1), (2,3), (4,5), ...
    for i in range(0, len(advancing_teams), 2):
        winner, loser = knockout_match(advancing_teams[i], advancing_teams[i+1])
        next_round.append(winner)

        if round_name == "SEMI-FINALS":
            semi_final_losers.append(loser)

        time.sleep(0.1)

    advancing_teams = next_round

    # Check tournament status
    if len(advancing_teams) == 2:
        print(f"\n✅ {round_name} complete. The finalists are ready!")
    elif len(advancing_teams) == 1:
        # Tournament finished
        print("\n🥉 THIRD-PLACE PLAYOFF 🥉")
        bronze_winner, _ = knockout_match(semi_final_losers[0], semi_final_losers[1], track_stats=False)
        print(f"🥉 BRONZE MEDAL: {bronze_winner}!")

        print("\n👑 " + "=" * 40 + " 👑")
        print(f"🏆 {advancing_teams[0].upper()} ARE THE WORLD CUP CHAMPIONS! 🏆")
        print("👑 " + "=" * 40 + " 👑")

        # Award for the team that scored the most goals
        highest_scoring_team = max(standings.keys(), key=lambda team: standings[team]["GF"])
        goals_scored = standings[highest_scoring_team]["GF"]
        print(f"\n🔥 HIGHEST SCORING TEAM: {highest_scoring_team} scored {goals_scored} goals!")

        if upsets_logged:
            print("\n⭐ CINDERELLA MOMENTS:")
            for upset in upsets_logged:
                print(f"   {upset}")

        advancing_teams = []  # reset for next tournament
    else:
        print(f"\n✅ {round_name} complete. {len(advancing_teams)} teams remain.")

    return True


# ============================================================
# INTERACTIVE MENUS
# ============================================================
def stage_by_stage_menu():
    """Let the user advance one round at a time."""
    phase = "Groups"
    while True:
        print(f"\n--- 🛠️  STEP-BY-STEP CONTROLLER (Next: {phase.upper()}) ---")
        print("1. Simulate Next Phase")
        print("2. View Current Knockout Bracket Pool")
        print("3. Return to Main Menu")

        choice = input("Select 1-3: ").strip()

        if choice == "1":
            if phase == "Groups":
                live = input("Show live match updates? (y/n): ").strip().lower() == 'y'
                simulate_group_stage(live)
                print("\n🎉 Group Stage done! 32 teams advanced.")
                phase = "Round of 32"
            elif phase == "Round of 32":
                if run_knockout_round("ROUND OF 32"):
                    phase = "Round of 16"
            elif phase == "Round of 16":
                if run_knockout_round("ROUND OF 16"):
                    phase = "Quarter-Finals"
            elif phase == "Quarter-Finals":
                if run_knockout_round("QUARTER-FINALS"):
                    phase = "Semi-Finals"
            elif phase == "Semi-Finals":
                if run_knockout_round("SEMI-FINALS"):
                    phase = "Final"
            elif phase == "Final":
                run_knockout_round("WORLD CUP FINAL")
                break  # tournament done, back to main menu

        elif choice == "2":
            if phase == "Groups":
                print("\n📋 Group stage not yet run. Start it first.")
            else:
                print(f"\n📋 Knockout pool ({len(advancing_teams)} teams left):")
                print(", ".join(advancing_teams))
        elif choice == "3":
            break


def show_groups_and_ranks():
    """Print all groups with each team's FIFA ranking."""
    print("\n=== WORLD CUP 2026 GROUPS ===")
    for group_name, team_list in GROUPS.items():
        print(f"\n📌 {group_name}:")
        for team in team_list:
            rank = FIFA_RANKINGS.get(team, "?")
            print(f"   {team} (Rank {rank})")


def show_group_standings(group_letter):
    """Display standings for a specific group (after group stage)."""
    group_name = f"Group {group_letter.upper()}"
    if group_name not in GROUPS:
        print("❌ Invalid group letter. Use A through L.")
        return

    # If no matches played, show a warning
    any_match_played = any(standings[team]["MP"] > 0 for team in GROUPS[group_name])
    if not any_match_played:
        print("\n⚠️ Group stage not simulated yet. Showing empty table.")

    print(f"\n=== {group_name} STANDINGS ===")
    print(f"{'Team':<25} | MP | W | D | L | GF | GA | PTS")
    print("-" * 55)

    # Sort by points, then goal difference, then goals scored
    sorted_teams = sorted(GROUPS[group_name], key=lambda team: (
        standings[team]["PTS"],
        standings[team]["GF"] - standings[team]["GA"],
        standings[team]["GF"]
    ), reverse=True)

    for team in sorted_teams:
        s = standings[team]
        print(f"{team:<25} | {s['MP']:2} | {s['W']:1} | {s['D']:1} | {s['L']:1} | "
              f"{s['GF']:2} | {s['GA']:2} | {s['PTS']:2}")


# ============================================================
# MAIN MENU
# ============================================================
def main():
    group_stage_run = False

    while True:
        print("\n" + "=" * 45)
        print("🏆 WORLD CUP 2026 SIMULATOR (Student Edition) 🏆")
        print("=" * 45)
        print("1. View Groups & FIFA Rankings")
        print("2. Step‑by‑Step Simulation")
        print("3. Run Full Tournament Automatically")
        print("4. View Group Standings")
        print("5. Exit")
        print("-" * 45)

        choice = input("Choose 1-5: ").strip()

        if choice == "1":
            show_groups_and_ranks()
        elif choice == "2":
            stage_by_stage_menu()
            group_stage_run = True
        elif choice == "3":
            live = input("Show live match updates during groups? (y/n): ").strip().lower() == 'y'
            simulate_group_stage(live)
            group_stage_run = True

            print("\n🚀 Running automatic knockout rounds...")
            input("Press Enter for Round of 32...")
            run_knockout_round("ROUND OF 32")
            input("\nPress Enter for Round of 16...")
            run_knockout_round("ROUND OF 16")
            input("\nPress Enter for Quarter‑Finals...")
            run_knockout_round("QUARTER-FINALS")
            input("\nPress Enter for Semi‑Finals...")
            run_knockout_round("SEMI-FINALS")
            input("\nPress Enter for the Finals...")
            run_knockout_round("WORLD CUP FINAL")
        elif choice == "4":
            if not group_stage_run:
                print("\n⚠️ You haven't simulated the group stage yet. Standings will be empty.")
            group_letter = input("Enter group letter (A-L): ").strip()
            show_group_standings(group_letter)
        elif choice == "5":
            print("\n👋 Thanks for simulating!")
            break


if __name__ == "__main__":
    main()
