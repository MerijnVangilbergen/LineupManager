# LineupManager
This is a GUI to manage the lineup in sport games (in this case futsal, but can be generalized)
The language used in this program is a mixture of English and Dutch.

- During start-up, I forgot to enter one name and I couldn't add it without restarting the program.
- When we reached half-time or the end of the game, I didn't have any visuals to show. I could generate a pie chart of minutes played or a histogram of play durations.
- The program creates a log file and a summary csv file. If the program is run twice on the same day, it puts both logs in the same file and the second csv overwrites the first csv. To be solved.
- The log file shows substitutes that happened before the game started. Fix this. Also, substitutions during a pause shouldn't be stored. Only the init line-up when the game starts again.