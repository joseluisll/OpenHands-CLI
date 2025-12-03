# Exit Modal Button Visibility Fix

## Problem Description
The exit modal's buttons were not visible when the terminal was of a small size, even though there was sufficient space for the buttons themselves.

## Root Cause Analysis
The issue was in the CSS file `openhands_cli/refactor/modals/exit_modal.tcss`. Several problematic styling rules caused the buttons to be hidden or improperly sized:

### Issues Identified:

1. **Incorrect height unit**: `height: 5vw` used viewport WIDTH units for height, which doesn't make sense
2. **Too small width**: `width: 25vw` (25% of viewport width) was too narrow for small terminals
3. **Restrictive grid layout**: `grid-rows: 1fr 3` gave buttons only 3 units of height with a very small total height
4. **No minimum dimensions**: Modal could become too small to be usable
5. **No explicit button height**: Buttons had no guaranteed vertical space

## Solution Applied

### Changes Made to `exit_modal.tcss`:

```css
/* BEFORE */
#dialog {
    grid-size: 2;
    grid-gutter: 1 2;
    grid-rows: 1fr 3;          /* Fixed button height */
    padding: 0 1;
    width: 25vw;               /* Too small */
    height: 5vw;               /* Wrong unit */
    border: $primary 80%;
    background: $surface 90%;
    margin: 1 1;
}

Button {
    width: 100%;
    margin: 0 1;               /* No explicit height */
}

/* AFTER */
#dialog {
    grid-size: 2;
    grid-gutter: 1 2;
    grid-rows: 1fr auto;       /* Auto-sizing for buttons */
    padding: 0 1;
    width: 60;                 /* Fixed character units */
    height: auto;              /* Auto-sizing */
    min-width: 40;             /* Minimum usable width */
    min-height: 7;             /* Minimum usable height */
    border: $primary 80%;
    background: $surface 90%;
    margin: 1 1;
}

Button {
    width: 100%;
    height: 3;                 /* Explicit button height */
    margin: 0 1;
}
```

### Key Improvements:

1. **Fixed height units**: Changed from `5vw` to `auto` for proper content-based sizing
2. **Adequate width**: Changed from `25vw` to `60` character units for consistent sizing
3. **Flexible grid**: Changed from `1fr 3` to `1fr auto` so buttons get the space they need
4. **Minimum dimensions**: Added `min-width: 40` and `min-height: 7` to ensure usability
5. **Explicit button height**: Added `height: 3` to guarantee button visibility

## Expected Results

After these changes:
- ✅ Modal maintains adequate size even on very small terminals
- ✅ Buttons are always visible and clickable
- ✅ Layout is consistent across different terminal sizes
- ✅ Modal automatically adjusts to content while respecting minimum dimensions
- ✅ Uses character-based units for predictable sizing in terminal environments

## Testing Recommendations

To verify the fix:
1. Run the application in a small terminal (e.g., 40x15 characters)
2. Trigger the exit modal (Ctrl+C or `/exit` command)
3. Confirm both "Yes, proceed" and "No, dismiss" buttons are visible and clickable
4. Test on various terminal sizes to ensure consistent behavior