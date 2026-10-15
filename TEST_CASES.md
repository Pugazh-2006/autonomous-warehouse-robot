# Autonomous Warehouse Robot — Test Cases

## Test setup

Start the application and use the **Starter Map** unless the test case says otherwise. A pathway can be blocked from the **Pathways** tab or by clicking the corresponding corridor on the map.

| TC | Test scenario | Input / action | Expected output |
| --- | --- | --- | --- |
| TC01 | BFS finds the direct shortest route | Starter Map. Source: `S` Storage Area. Destination: `C` Packing Station. Algorithm: BFS. No blocked pathways. Click **Find Route**. | A route is found: `S → A → C`. Path length is `2 edges`. The result panel says BFS and confirms that the route is shortest. |
| TC02 | BFS chooses the shorter of two available routes | Starter Map. Source: `S`. Destination: `D` Exit. Algorithm: BFS. No blocked pathways. | A route is found: `S → B → D`. Path length is `2 edges`, even though the longer route `S → A → C → D` also exists. |
| TC03 | DFS follows a deeper valid branch | Starter Map. Source: `S`. Destination: `D`. Algorithm: DFS. No blocked pathways. | A valid route is found: `S → A → C → D`. Path length is `3 edges`. The result reports that DFS does not guarantee the shortest route. |
| TC04 | BFS reroutes around one blocked corridor | Starter Map. Block `A ↔ C`. Source: `S`. Destination: `C`. Algorithm: BFS. | The blocked corridor is not used. A detour is found: `S → B → D → C`, with `3 edges`. The result lists `A-C` as blocked. |
| TC05 | Robot reports no route when the start is isolated | Starter Map. Block `S ↔ A` and `S ↔ B`. Source: `S`. Destination: `C`. Algorithm: BFS. | The application reports **No Route Available**. The path area explains that no route exists between the selected locations. It must not show a successful route. |
| TC06 | Start location is the destination | Starter Map. Source: `S`. Destination: `S`. Run BFS, then run DFS. | Both algorithms immediately report a valid route with `0 edges` and `1 visited node`. The result badge states that source is destination. |
| TC07 | Reopening corridors restores navigation | Complete TC05, then click **Reopen All Pathways**. Source: `S`. Destination: `C`. Algorithm: BFS. | All pathway tags return to OPEN. BFS finds `S → A → C` again. |
| TC08 | Blockage invalidates an old route | Find a route on Starter Map. Then block a corridor that belongs to that displayed route. | The old route and its color markers are cleared because it is no longer valid. The user can run a new search to calculate a detour. |
| TC09 | Large Warehouse loads and searches correctly | Choose **Large Warehouse**. Source: `N02` Inbound Dock 3. Destination: `N92` Packing Hub 3. Algorithm: BFS. | The map loads with `50 nodes` and `78 pathways`. BFS finds the shortest available route. With no blocked pathways, the expected route length is `9 edges`. |
| TC10 | BFS and DFS can be compared on the same large map | Large Warehouse. Source: `N02`. Destination: `N92`. First run BFS, then DFS. | BFS reports a `9-edge` shortest route. DFS returns a valid route but may be much longer; its result clearly states that it is not guaranteed to be shortest. |
| TC11 | Random map is reproducible from its seed | Select Random Warehouse. Enter seed `42`, then click **Generate**. Repeat with seed `42`. | Both generated maps have the same node count, locations, and pathways. Changing the seed creates a different connected map. |
| TC12 | Map switching resets map-specific data | Run a route or block corridors on one map. Select a different predefined map. | The new map loads immediately. Its source and destination options update, old route results are cleared, and blocked pathways do not carry over. |
| TC13 | Fit View keeps the search result visible | Find any route. Zoom or pan the map. Click **Fit View**. | The full map returns to view. The source stays teal, destination stays pink, final route stays blue, and visited nodes keep their search colors. |
| TC14 | Zoom and pan stay within usable map space | Use the mouse wheel or `+` / `−` controls. Hold the middle mouse button and drag the map. | The map zooms and pans smoothly. The dashed boundary shows the active map area. Zoom limits prevent the view from becoming unusable. |
| TC15 | Node inspection shows meaningful details | Click any node in the warehouse map. | The Route tab shows the selected location's readable name, node ID, type, coordinates, and connected corridors. |
| TC16 | Search playback follows the selected algorithm | Find a route, then click **Play Search**. Try **Pause**, **Resume**, and **Stop Playback**. | The animation shows visited nodes in search order, then traces the final robot route. Pause freezes the playback, Resume continues it, and Stop returns to the complete route result. |
| TC17 | Theme switching keeps the current workspace | Load a map and find a route. Switch between Light mode and Dark mode. | The colors and panels change theme, while the selected map, route, result values, and controls remain available. |
| TC18 | Clearing the search does not alter the warehouse | Find a route, then click **Clear Search**. | Route metrics, visited steps, and route colors are cleared. The selected map, source, destination, and current pathway states remain unchanged. |

## Test result record

Use this small record while demonstrating the project to a client or evaluator.

| TC | Tester | Date | Result | Notes |
| --- | --- | --- | --- | --- |
| TC01–TC18 |  |  | Pass / Fail |  |
