# LineupManager
This is a GUI to manage the lineup in sport games (in this case futsal, but can be generalized)
The language used in this program is a mixture of English and Dutch.

- During start-up, I forgot to enter one name and I couldn't add it without restarting the program.
- When we reached half-time or the end of the game, I didn't have any visuals to show. I could generate a pie chart of minutes played or a histogram of play durations.
- After the game, a player proposed to always have one player ready for substitution for each position on the field. This raises the idea to make the dashboard visualize the 5 positions on the field and make a reservation slot for each. I think it would be nice if we could drag players from the bench to the reservation spot.
- The program creates a log file and a summary csv file. If the program is run twice on the same day, it puts both logs in the same file and the second csv overwrites the first csv. To be solved.
- Undo button to be added.

cleaning tkinter code:
- The highlight of a rectangular box should be done by setting outline. 
    See https://anzeljg.github.io/rin2/book2/2405/docs/tkinter/create_rectangle.html
    For this, store all rectangles as attributes to the dashboard object.
- Use grid to structure the dashboard:
    See https://tkdocs.com/tutorial/grid.html