def print_board(player, obstacles, fuel_depots, missiles):
    board = [[" " for _ in range(10)] for _ in range(10)]

    # Add player
    board[player.y][player.x] = "P"

    # Add obstacles
    for obs in obstacles:
        if 0 <= obs.y < 10:
            board[obs.y][obs.x] = "O"

    # Add fuel
    for depot in fuel_depots:
        if 0 <= depot.y < 10:
            board[depot.y][depot.x] = "F"

    # Add missiles
    for missile in missiles:
        if 0 <= missile.y < 10:
            board[missile.y][missile.x] = "|"

    for row in board:
        print("".join(row))
