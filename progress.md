Original prompt: please make them

- Added a cleaner project structure with static/css and static/js.
- Moved inline styles and scripts out of templates/index.html and templates/host.html.
- Added requirements.txt with the current Flask dependency.
- Kept the existing backend route structure and gameplay flow unchanged.

TODOs
- Verify the player and host pages in a browser after the asset split.
- Consider moving Flask game state logic out of app.py before the v0.2.0 lobby refactor.
- Update README setup docs later if more dependencies are introduced.
