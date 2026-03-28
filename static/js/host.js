let currentPhase = "";
let loading = false;

document.getElementById("startBtn").addEventListener("click", startGame);
document.getElementById("resolveBtn").addEventListener("click", resolveNight);
document.getElementById("startVoteBtn").addEventListener("click", startVoting);
document.getElementById("endVoteBtn").addEventListener("click", endVoting);
document.getElementById("endGameBtn").addEventListener("click", endGame);

function safeFetch(url, options = {}) {
    if (loading) {
        return Promise.resolve(null);
    }

    loading = true;

    return fetch(url, options)
        .then((res) => res.json())
        .then((data) => {
            loading = false;

            if (data.error) {
                setStatus("Error: " + data.error);
                return null;
            }

            return data;
        })
        .catch(() => {
            loading = false;
            setStatus("Error: Network error");
        });
}

function setStatus(message) {
    document.getElementById("status").innerText = message;
}

function startGame() {
    safeFetch("/start", { method: "POST" }).then((data) => {
        if (data) {
            setStatus("Game started");
        }
    });
}

function resolveNight() {
    safeFetch("/resolve", { method: "POST" }).then((data) => {
        if (data) {
            setStatus("Night resolved. Eliminated: " + (data.eliminated || "Nobody"));
        }
    });
}

function startVoting() {
    safeFetch("/start_voting", { method: "POST" }).then((data) => {
        if (data) {
            setStatus("Voting started");
        }
    });
}

function endVoting() {
    safeFetch("/end_vote", { method: "POST" }).then((data) => {
        if (data) {
            setStatus("Voting ended. Eliminated: " + (data.eliminated || "Nobody"));
        }
    });
}

function loadPlayers() {
    fetch("/players")
        .then((r) => r.json())
        .then((players) => {
            const list = document.getElementById("players");
            list.innerHTML = "";
            players.forEach((player) => {
                list.innerHTML += `<li>${player}</li>`;
            });
        });
}

function loadRoles() {
    fetch("/all_roles")
        .then((r) => r.json())
        .then((data) => {
            const list = document.getElementById("roles");
            list.innerHTML = "";
            Object.keys(data).forEach((name) => {
                list.innerHTML += `<li>${name} -> ${data[name]}</li>`;
            });
        });
}

function loadActions() {
    fetch("/actions")
        .then((r) => r.json())
        .then((data) => {
            const list = document.getElementById("actions");
            list.innerHTML = "";

            list.innerHTML += `<li>Doctor -> ${data.doctor || "-"}</li>`;
            list.innerHTML += `<li>Police -> ${data.police || "-"}</li>`;

            const mafiaVotes = data.mafia_votes || {};
            if (!Object.keys(mafiaVotes).length) {
                list.innerHTML += "<li>Mafia -> -</li>";
            } else {
                Object.keys(mafiaVotes).forEach((mafiaPlayer) => {
                    list.innerHTML += `<li>Mafia (${mafiaPlayer}) -> ${mafiaVotes[mafiaPlayer]}</li>`;
                });
            }
        });
}

function loadSuggestions() {
    fetch("/suggestions")
        .then((r) => r.json())
        .then((data) => {
            const list = document.getElementById("suggestions");
            list.innerHTML = "";

            if (!Object.keys(data).length) {
                list.innerHTML = "<li>-</li>";
                return;
            }

            Object.keys(data).forEach((mafiaPlayer) => {
                list.innerHTML += `<li>${mafiaPlayer} -> ${data[mafiaPlayer]}</li>`;
            });
        });
}

function loadGameState() {
    fetch("/game_state")
        .then((r) => r.json())
        .then((state) => {
            currentPhase = state.phase;
            document.getElementById("gameInfo").innerText =
                `Round: ${state.round} | Phase: ${state.phase}`;

            renderList(state.alive || [], "alivePlayers", "No alive players");
            renderList(state.eliminated || [], "deadPlayers", "No dead players");

            if (state.phase === "waiting") {
                document.getElementById("winner").innerText = "";
            }

            if (state.winner) {
                document.getElementById("winner").innerText = "Winner: " + state.winner;
            }

            updateButtons(currentPhase);
        });
}

function loadVotes() {
    fetch("/votes")
        .then((r) => r.json())
        .then((data) => {
            const countsList = document.getElementById("voteCounts");
            const detailsList = document.getElementById("voteDetails");

            countsList.innerHTML = "";
            detailsList.innerHTML = "";

            Object.keys(data.counts).forEach((target) => {
                countsList.innerHTML += `<li>${target} -> ${data.counts[target]}</li>`;
            });

            Object.keys(data.individual).forEach((voter) => {
                detailsList.innerHTML += `<li>${voter} -> ${data.individual[voter]}</li>`;
            });
        });
}

function loadVoteHistory() {
    fetch("/vote_history")
        .then((r) => r.json())
        .then((history) => {
            const list = document.getElementById("voteHistory");
            list.innerHTML = "";

            history.forEach((entry) => {
                list.innerHTML += `
                    <li>
                        Round ${entry.round} | Eliminated: ${entry.eliminated} | Votes: ${JSON.stringify(entry.votes)}
                    </li>
                `;
            });
        });
}

function updateButtons(phase) {
    document.getElementById("startBtn").disabled = phase !== "waiting";
    document.getElementById("resolveBtn").disabled = phase !== "night";
    document.getElementById("startVoteBtn").disabled = phase !== "day";
    document.getElementById("endVoteBtn").disabled = phase !== "voting";
}

function renderList(items, id, emptyMessage = "-") {
    const list = document.getElementById(id);
    list.innerHTML = "";

    if (!items.length) {
        list.innerHTML = `<li>${emptyMessage}</li>`;
        return;
    }

    items.forEach((item) => {
        list.innerHTML += `<li>${item}</li>`;
    });
}

function endGame() {
    if (!confirm("End game?")) {
        return;
    }

    fetch("/reset", { method: "POST" }).then(() => {
        setStatus("Game reset");
        location.reload();
    });
}

setInterval(() => {
    loadPlayers();
    loadRoles();
    loadActions();
    loadSuggestions();
    loadGameState();
    loadVotes();
    loadVoteHistory();
}, 2000);
