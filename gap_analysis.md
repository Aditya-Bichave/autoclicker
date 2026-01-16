# Gap Analysis & Implementation Plan

1.  *Click Count Limit*
    - Status: Not implemented in UI or Engine.
    - Plan: Add "Click Limit" QSpinBox to `click_tab` (0 = infinite). Update Engine to check limit.

2.  *Burst Mode*
    - Status: "grouped" exists, but full burst (size + interval) is partial.
    - Plan: Add "Burst Size" and "Burst Interval" to `tuning_tab`. Update Engine to use them if mode is "grouped" or new "burst" mode. "Grouped" currently just splits points in half.
    - Decision: Add a specific "Burst" mode to dropdown? Or make "grouped" use burst parameters?
    - Simplest: Add "Burst" mode to `click_mode` combo.

3.  *Game-safe Mode*
    - Status: Jitter exists. "Game-safe" usually implies "Human-like" (random interval curves).
    - Plan: Add "Human-like" toggle in `tuning_tab`. If enabled, use a randomization algorithm for delays (e.g. normal distribution) instead of simple uniform jitter.

4.  *Inline Editing*
    - Status: `PointModel` has `setData` parsing "x,y".
    - Plan: `QListView` edits usually require double click. `Qt.ItemIsEditable` is set.
    - Verification: Should work. I will add a test to confirm `setData` works with string input.

5.  *Group Assignment*
    - Status: Missing UI.
    - Plan: Add "Set Group" to context menu in `MainWindow`. Updates `PointModel`.

6.  *Macro Resolution Independence*
    - Status: Recorder saves raw coords.
    - Plan: Normalize to 0.0-1.0 based on screen size during record. Denormalize during playback.
    - NOTE: This might break if resolution changes. But requested.
    - Implementation: `MacroRecorder` gets screen size (via `user32` or `QScreen`). Saves relative. `MacroPlayer` scales back.

7.  *Logs Panel*
    - Status: Optional. Skipped for now to focus on core gaps.

**Revised Plan:**
1.  Add "Click Limit" to UI and Engine.
2.  Add "Burst Mode" to UI and Engine.
3.  Add "Set Group" to Point Context Menu.
4.  Implement "Macro Normalization" (Scale coords).
5.  Implement "Human-like" delay randomization in Engine.
6.  Final Verification.
