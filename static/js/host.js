const appConfig = window.APP_CONFIG || {};
const gameMode = appConfig.game_mode || "dedicated-host";

let currentPhase = "";
let loading = false;
let hostAuthorized = false;

const startBtn = document.getElementById("startBtn");
const resolveBtn = document.getElementById("resolveBtn");
const startVoteBtn = document.getElementById("startVoteBtn");
const endVoteBtn = document.getElementById("endVoteBtn");
const endGameBtn = document.getElementById("endGameBtn");
const hostLoginBtn = document.getElementById("hostLoginBtn");
const hostAccessCodeInput = document.getElementById("hostAccessCode");

if (startBtn) {
    startBtn.addEventListener("click", startGame);
}
resolveBtn.addEventListener("click", resolveNight);
startVoteBtn.addEventListener("click", startVoting);
endVoteBtn.addEventListener("click", endVoting);
endGameBtn.addEventListener("click", endGame);
if (hostLoginBtn) {
    hostLoginBtn.addEventListener("click", loginHost);
}
if (hostAccessCodeInput) {
    hostAccessCodeInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            loginHost();
        }
    });
}

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

function setAuthStatus(message) {
    document.getElementById("authStatus").innerText = message;
}

function updateHostAccessUi() {
    document.getElementById("hostAuthPanel").classList.toggle("hidden", hostAuthorized);
    document.getElementById("hostPanel").classList.toggle("hidden", !hostAuthorized);
}

function loginHost() {
    if (gameMode !== "dedicated-host" || !hostAccessCodeInput) {
        return;
    }

    const accessCode = hostAccessCodeInput.value.trim();

    if (!accessCode) {
        setAuthStatus("Enter the host access code to continue.");
        return;
    }

    fetch("/host/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ access_code: accessCode })
    })
        .then((response) =>
            response.json().then((data) => ({
                ok: response.ok,
                data
            }))
        )
        .then(({ ok, data }) => {
            hostAuthorized = ok && Boolean(data.authorized);
            updateHostAccessUi();
            setAuthStatus(hostAuthorized ? "Host panel unlocked." : (data.error || "Access denied"));
            if (hostAuthorized) {
                hostAccessCodeInput.value = "";
                loadAllHostData();
            }
        })
        .catch(() => {
            hostAuthorized = false;
            updateHostAccessUi();
            setAuthStatus("Unable to unlock the host panel right now.");
        });
}

function autoClaimHost(name) {
    if (!name) {
        return Promise.resolve(false);
    }

    return fetch("/host/claim", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name })
    })
        .then((response) =>
            response.json().then((data) => ({
                ok: response.ok,
                data
            }))
        )
        .then(({ ok, data }) => {
            hostAuthorized = ok && Boolean(data.authorized);
            updateHostAccessUi();
            setAuthStatus(hostAuthorized ? "" : (data.error || "Access denied"));
            if (hostAuthorized) {
                loadAllHostData();
                window.history.replaceState({}, document.title, "/host");
            }
            return hostAuthorized;
        })
        .catch(() => {
            setAuthStatus("Unable to verify host access.");
            return false;
        });
}

function loadHostStatus() {
    fetch("/host/status")
        .then((response) => response.json())
        .then((data) => {
            hostAuthorized = Boolean(data.authorized);
            updateHostAccessUi();

            if (gameMode === "lobby-ready") {
                const label = document.getElementById("assignedHostLabel");
                if (label) {
                    if (!data.game_started) {
                        label.innerText = "No host yet. Once all players ready up, one joined player will be assigned automatically.";
                    } else if (data.assigned_host) {
                        label.innerText = "Assigned host: " + data.assigned_host;
                    } else {
                        label.innerText = "Host assignment unavailable.";
                    }
                }

                setAuthStatus(
                    hostAuthorized
                        ? ""
                        : "Open this page from the assigned host player's game screen."
                );

                if (hostAuthorized) {
                    loadAllHostData();
                    return;
                }

                const playerName = new URLSearchParams(window.location.search).get("player_name");
                if (playerName && data.assigned_host === playerName) {
                    autoClaimHost(playerName);
                }
                return;
            }

            if (hostAuthorized) {
                loadAllHostData();
                return;
            }

            setAuthStatus("Enter the host access code to continue.");
        });
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
            setStatus(data.message || ("Voting ended. Eliminated: " + (data.eliminated || "Nobody")));
        }
    });
}

function loadPlayers() {
    fetch("/players")
        .then((r) => r.json())
        .then((players) => {
            renderList(players, "players", "No joined players");
        });
}

function loadRoles() {
    fetch("/all_roles")
        .then((r) => r.json())
        .then((data) => {
            const list = document.getElementById("roles");
            list.innerHTML = "";

            if (!Object.keys(data).length) {
                list.innerHTML = "<li>No roles assigned yet</li>";
                return;
            }

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

            list.innerHTML += `
                <li>
                    Doctor (${data.doctor_player || "-"}) -> ${formatRoleActionStatus(
                        data.doctor_status,
                        data.doctor
                    )}
                </li>
            `;
            list.innerHTML += `
                <li>
                    Police (${data.police_player || "-"}) -> ${formatRoleActionStatus(
                        data.police_status,
                        data.police
                    )}
                </li>
            `;

            const mafiaVotes = data.mafia_votes || {};
            const aliveMafia = data.mafia_alive || [];
            const eliminatedMafia = data.mafia_eliminated || [];

            if (!aliveMafia.length && !eliminatedMafia.length) {
                list.innerHTML += "<li>Mafia -> Unavailable</li>";
                return;
            }

            aliveMafia.forEach((mafiaPlayer) => {
                list.innerHTML += `
                    <li>
                        Mafia (${mafiaPlayer}) -> ${mafiaVotes[mafiaPlayer] || "Pending"}
                    </li>
                `;
            });

            eliminatedMafia.forEach((mafiaPlayer) => {
                list.innerHTML += `<li>Mafia (${mafiaPlayer}) -> Eliminated</li>`;
            });
        });
}

function formatRoleActionStatus(status, actionValue) {
    if (status === "Submitted") {
        return actionValue;
    }
    return status || "-";
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

            if (!Object.keys(data.counts).length) {
                countsList.innerHTML = "<li>No live votes</li>";
            }

            Object.keys(data.counts).forEach((target) => {
                countsList.innerHTML += `<li>${target} -> ${data.counts[target]}</li>`;
            });

            if (!Object.keys(data.individual).length) {
                detailsList.innerHTML = "<li>No votes submitted yet</li>";
            }

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

            if (!history.length) {
                list.innerHTML = "<li>No vote history yet</li>";
                return;
            }

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
    if (startBtn) {
        startBtn.disabled = phase !== "waiting";
    }
    resolveBtn.disabled = phase !== "night";
    startVoteBtn.disabled = phase !== "day";
    endVoteBtn.disabled = phase !== "voting";
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
    if (!hostAuthorized) {
        return;
    }

    loadAllHostData();
}, 2000);

function loadAllHostData() {
    loadPlayers();
    loadRoles();
    loadActions();
    loadSuggestions();
    loadGameState();
    loadVotes();
    loadVoteHistory();
}

loadHostStatus();
