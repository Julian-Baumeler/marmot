import math

RADIUS = 80          
TOTAL_STEPS = 200    # motor steps for fully open
DEAD_STEPS = 40     # steps before valve starts opening
ACTIVE_STEPS = TOTAL_STEPS - DEAD_STEPS  
MAX_HEIGHT = 2 * RADIUS                  


def circular_segment_area(r: float, h: float) -> float:
    """
    Calculates the area of a circular segment.

    Formula: A = r² · arccos(1 - h/r) - (r - h) · √(2rh - h²)

    Parameters:
        r (float): Radius of the circle
        h (float): Height of the segment

    Returns:
        float: Area of the circular segment
    """
    if r <= 0:
        raise ValueError("Radius r must be greater than 0.")

    arccos_part = r**2 * math.acos(1 - h / r)
    sqrt_part = (r - h) * math.sqrt(2 * r * h - h**2)

    return arccos_part - sqrt_part


def steps_to_height(steps: float) -> float:
    """
    Maps motor steps to effective segment height,
    accounting for the deadzone.

    Steps 0–40:   deadzone → h = 0
    Steps 40–200: active   → h = 0 to 160
    """
    effective_steps = max(0.0, steps - DEAD_STEPS) 
    return effective_steps


def percentage_of_area(steps: float) -> float:
    """
    Returns the open percentage (0–100%) for a given motor step position.
    """
    h = steps_to_height(steps)

    if h <= 0:
        return 0.0

    full_area = circular_segment_area(RADIUS, MAX_HEIGHT)
    curr_area = circular_segment_area(RADIUS, h)

    return 100.0 / full_area * curr_area


if __name__ == "__main__":
    print("=== Valve Opening Calculator ===")
    print(f"Radius: {RADIUS} | Total steps: {TOTAL_STEPS} | Deadzone: {DEAD_STEPS} steps\n")
    print(f"{'Steps':>8} | {'Height h':>10} | {'Open %':>8}")
    print("-" * 35)

    for s in range(201):
        h = steps_to_height(s)
        pct = percentage_of_area(s)
        print(f"{s:>8} | {h:>10.2f} | {pct:>7.2f}%")
