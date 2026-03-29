from mafia_game import create_app

app = create_app()
"""

players = []
roles = {}
game_started = False

game_state = {
    "round": 1,
    "phase": "waiting",
    "alive": [],
    "eliminated": [],
    "winner": None
}

actions = {"doctor": None, "police": None}
mafia_votes = {}
mafia_suggestions = {}  # ✅ NEW

police_reports = {}

votes = {}
voted = {}
vote_history = []

# ---------------- BASIC ROUTES ---------------- #

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/host")
def host():
    return render_template("host.html")

@app.route("/join", methods=["POST"])
def join():
    global game_started
    if game_started:
        return jsonify({"error": "Game started"}), 400

    name = request.json.get("name")
    if name and name not in players:
        players.append(name)

    return jsonify(players)

@app.route("/players")
def get_players():
    return jsonify(players)

# ---------------- START GAME ---------------- #

@app.route("/start", methods=["POST"])
def start_game():
    global game_started, roles, game_state
    global actions, police_reports, mafia_votes, mafia_suggestions
    global votes, voted, vote_history

    if len(players) < 4:
        return jsonify({"error": "Minimum 4 players required"}), 400

    game_started = True

    # 🔥 CLEAN STATE
    roles = {}
    police_reports = {}
    mafia_votes = {}
    mafia_suggestions = {}  # ✅ RESET
    votes = {}
    voted = {}
    vote_history = []
    actions = {"doctor": None, "police": None}

    shuffled = players[:]
    random.shuffle(shuffled)

    mafia_count = 2 if len(players) >= 6 else 1

    for i in range(mafia_count):
        roles[shuffled[i]] = "Mafia"

    roles[shuffled[mafia_count]] = "Doctor"

    police_player = shuffled[mafia_count + 1]
    roles[police_player] = "Police"
    police_reports[police_player] = []

    for p in shuffled[mafia_count + 2:]:
        roles[p] = "Villager"

    game_state = {
        "round": 1,
        "phase": "night",
        "alive": players[:],
        "eliminated": [],
        "winner": None
    }

    return jsonify({"message": "started"})

# ---------------- ROLE ---------------- #

@app.route("/role/<name>")
def get_role(name):
    if not game_started or name not in roles:
        return jsonify({"role": None})
    return jsonify({"role": roles[name]})

@app.route("/all_roles")
def all_roles():
    return jsonify(roles)

@app.route("/game_state")
def get_game_state():
    return jsonify(game_state)

# ---------------- ACTIONS ---------------- #

@app.route("/action", methods=["POST"])
def submit_action():
    global mafia_votes

    if game_state["phase"] != "night":
        return jsonify({"error": "Not night phase"}), 400

    data = request.json
    name = data["name"]
    target = data["target"]

    if name not in game_state["alive"]:
        return jsonify({"error": "Dead players cannot act"}), 400

    if target not in players:
        return jsonify({"error": "Invalid target"}), 400

    role = roles.get(name)

    if role == "Doctor":
        actions["doctor"] = target

    elif role == "Police":
        actions["police"] = target

    elif role == "Mafia":
        if roles.get(target) == "Mafia":
            return jsonify({"error": "Cannot target fellow mafia"}), 400

        mafia_votes[name] = target

    return jsonify({"ok": True})

# ---------------- MAFIA SUGGESTIONS ---------------- #

@app.route("/suggest", methods=["POST"])
def suggest():
    global mafia_suggestions

    if game_state["phase"] != "night":
        return jsonify({"error": "Not night phase"}), 400

    data = request.json
    name = data["name"]
    target = data["target"]

    if roles.get(name) != "Mafia":
        return jsonify({"error": "Only mafia can suggest"}), 400

    if name not in game_state["alive"]:
        return jsonify({"error": "Dead mafia cannot suggest"}), 400

    if target not in game_state["alive"]:
        return jsonify({"error": "Invalid target"}), 400

    if roles.get(target) == "Mafia":
        return jsonify({"error": "Cannot suggest mafia"}), 400

    mafia_suggestions[name] = target

    return jsonify({"ok": True})

@app.route("/suggestions")
def get_suggestions():
    return jsonify(mafia_suggestions)

# ---------------- ACTION VIEW ---------------- #

@app.route("/actions")
def get_actions():
    return jsonify({
        "doctor": actions["doctor"],
        "police": actions["police"],
        "mafia_votes": mafia_votes
    })

@app.route("/resolve", methods=["POST"])
def resolve_night():
    global actions, mafia_votes, mafia_suggestions

    if game_state["phase"] != "night":
        return jsonify({"error": "Not night phase"}), 400

    doctor_save = actions["doctor"]
    police_target = actions["police"]

    eliminated = None

    alive_mafia_votes = [
        target for m, target in mafia_votes.items()
        if m in game_state["alive"] and target in game_state["alive"]
    ]

    mafia_target = None

    if alive_mafia_votes:
        if len(set(alive_mafia_votes)) == 1:
            mafia_target = alive_mafia_votes[0]
        else:
            mafia_target = random.choice(alive_mafia_votes)

    if mafia_target and mafia_target != doctor_save:
        if mafia_target in game_state["alive"]:
            game_state["alive"].remove(mafia_target)
            game_state["eliminated"].append(mafia_target)
            eliminated = mafia_target

    if police_target:
        for p in police_reports:
            if roles.get(police_target) == "Mafia":
                police_reports[p].append(f"{police_target} is Mafia")
            else:
                police_reports[p].append(f"{police_target} is NOT Mafia")

    game_state["phase"] = "day"

    actions = {"doctor": None, "police": None}
    mafia_votes = {}
    mafia_suggestions = {}  # ✅ CLEAR AFTER NIGHT

    check_winner()

    return jsonify({"eliminated": eliminated})

# ---------------- VOTING ---------------- #

@app.route("/start_voting", methods=["POST"])
def start_voting():
    global votes, voted

    if game_state["phase"] != "day":
        return jsonify({"error": "Not day phase"}), 400

    votes = {}
    voted = {}

    game_state["phase"] = "voting"
    return jsonify({"message": "voting started"})

@app.route("/vote", methods=["POST"])
def vote():
    if game_state["phase"] != "voting":
        return jsonify({"error": "Voting not active"}), 400

    voter = request.json["name"]
    target = request.json["target"]

    if voter == target:
        return jsonify({"error": "Cannot vote yourself"}), 400

    if voter not in game_state["alive"]:
        return jsonify({"error": "Dead players cannot vote"}), 400

    if target not in game_state["alive"]:
        return jsonify({"error": "Invalid target"}), 400

    if voter in voted:
        prev = voted[voter]
        votes[prev] -= 1
        if votes[prev] <= 0:
            votes.pop(prev, None)

    voted[voter] = target
    votes[target] = votes.get(target, 0) + 1

    return jsonify({"message": "vote updated"})

@app.route("/votes")
def get_votes():
    return jsonify({
        "counts": votes,
        "individual": voted
    })

@app.route("/end_vote", methods=["POST"])
def end_vote():
    global votes, voted

    if game_state["phase"] != "voting":
        return jsonify({"error": "Voting not active"}), 400

    if not votes:
        return jsonify({"message": "No votes"})

    eliminated = max(votes, key=votes.get)

    if eliminated in game_state["alive"]:
        game_state["alive"].remove(eliminated)
        game_state["eliminated"].append(eliminated)

    vote_history.append({
        "round": game_state["round"],
        "votes": voted.copy(),
        "eliminated": eliminated
    })

    votes = {}
    voted = {}

    game_state["round"] += 1
    game_state["phase"] = "night"

    check_winner()

    return jsonify({"eliminated": eliminated})

@app.route("/vote_history")
def get_vote_history():
    return jsonify(vote_history)

# ---------------- RESET ---------------- #

@app.route("/reset", methods=["POST"])
def reset_game():
    global roles, game_started, game_state
    global actions, police_reports, votes, voted, vote_history
    global mafia_votes, mafia_suggestions

    roles = {}
    game_started = False

    game_state = {
        "round": 1,
        "phase": "waiting",
        "alive": [],
        "eliminated": [],
        "winner": None
    }

    actions = {"doctor": None, "police": None}
    mafia_votes = {}
    mafia_suggestions = {}  # ✅ RESET
    police_reports = {}

    votes = {}
    voted = {}
    vote_history = []

    return jsonify({"message": "Game reset"})

# ---------------- WIN CONDITION ---------------- #

def check_winner():
    alive = game_state["alive"]
    mafia = sum(1 for p in alive if roles.get(p) == "Mafia")
    others = len(alive) - mafia

    if mafia == 0:
        game_state["winner"] = "Villagers"
    elif mafia >= others:
        game_state["winner"] = "Mafia"

@app.route("/game_result")
def game_result():
    return jsonify({"winner": game_state["winner"]})

# ---------------- POLICE ---------------- #

@app.route("/police_reports/<name>")
def get_reports(name):
    return jsonify(police_reports.get(name, []))

@app.route("/next_round", methods=["POST"])
def next_round():
    game_state["round"] += 1
    game_state["phase"] = "night"
    return jsonify({"message": "next"})

"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
