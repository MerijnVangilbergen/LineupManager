import tkinter as tk
import numpy as np
import pandas as pd
import time
import logging


class Wedstrijd:
    def __init__(self, spelers):
        # Set up logging configuration
        today = time.strftime("%Y-%m-%d")
        logging.basicConfig(filename=f'wedstrijd_{today}.log', 
                            level=logging.INFO, 
                            format='%(asctime)s - %(levelname)s - %(message)s')
        self.log_function_call("__init__", spelers)
    
        # Create a DataFrame to keep track of the players
        self.spelers = pd.DataFrame(index=spelers)
        self.spelers["Actief"] = False
        self.spelers['Spot'] = np.arange(len(spelers))
        self.spelers["Gespeeld"] = 0.0
        self.spelers["Laatste wijziging"] = np.nan

    def log_function_call(self, function_name, *args):
        """Logs the function calls with their arguments."""
        logging.info(f'{function_name}({args})')

    def init_opstelling(self, *spelers):
        self.log_function_call("init_opstelling", *spelers)
        self.spelers.loc[spelers, "Actief"] = True
        self.spelers.loc[spelers, 'Spot'] = np.arange(len(spelers))
        andere_spelers = self.spelers.index.difference(spelers)
        self.spelers.loc[andere_spelers, "Spot"] = np.arange(len(andere_spelers))

    def start(self, tijdstip):
        self.log_function_call("start")
        self.spelers["Laatste wijziging"] = np.where(self.spelers["Actief"], tijdstip, -np.inf)

    def end(self, tijdstip):
        self.log_function_call("end")
        self.spelers.loc[self.spelers["Actief"], "Gespeeld"] += tijdstip - self.spelers.loc[self.spelers["Actief"], "Laatste wijziging"]
        self.spelers["Laatste wijziging"] = tijdstip
        self.spelers['Gespeeld'] = [time.strftime("%M:%S", time.gmtime(tijd)) for tijd in self.spelers['Gespeeld']] # format mm:ss
        self.spelers['Gespeeld'].to_csv('wedstrijdoverzicht.csv')

    def add_pause(self, begin, einde):
        self.log_function_call("pause")
        self.spelers.loc[self.spelers["Actief"], "Laatste wijziging"] += einde - begin

    def wissel(self, speler_uit, speler_in, tijdstip):
        self.log_function_call("wissel", speler_uit, speler_in)

        # naar de bank
        self.spelers.at[speler_uit, "Actief"] = False
        self.spelers.at[speler_uit, "Gespeeld"] += tijdstip - self.spelers.at[speler_uit, "Laatste wijziging"]
        self.spelers.at[speler_uit, "Laatste wijziging"] = tijdstip

        # van de bank
        self.spelers.at[speler_in, "Actief"] = True
        self.spelers.at[speler_in, "Laatste wijziging"] = tijdstip

        self.spelers.at[speler_in, 'Spot'], self.spelers.at[speler_uit, 'Spot'] = self.spelers.at[speler_uit, 'Spot'], self.spelers.at[speler_in, 'Spot']


class Dashboard():
    def __init__(self):
        self.paused = False
        self.active_selection = None
        self.bench_selection = None

        # Create main window
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.scale_factor = screen_height / 1080  # Reference height is 1080px, adjust for others

        # Configuration: Define sizes and colors
        self.ACTIVE_COLOR = "lightgreen"
        self.BENCH_COLOR = "lightblue"
        self.ACTIVE_RECT_SIZE = (int(screen_width * .4), int(screen_height * .075))  # Active player rectangles
        self.BENCH_RECT_SIZE = (int(screen_width * .4), int(screen_height * .045))  # Bench player rectangles
        self.spacing = int(screen_height * .04)  # Spacing between rectangles

        # Create a frame to organize the layout in full screen
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create subtitles for active players and bench players
        active_label = tk.Label(self.main_frame, text="Het veld", font=("Helvetica", int(16 * self.scale_factor)))
        bench_label = tk.Label(self.main_frame, text="De bank", font=("Helvetica", int(16 * self.scale_factor)))

        # Create canvases for active and bench players inside the frame
        self.canvas_active = tk.Canvas(self.main_frame, bg="white")
        self.canvas_bench = tk.Canvas(self.main_frame, bg="white")
        
        # Organize the widgets using grid layout
        active_label.grid(row=0, column=0, padx=self.spacing, pady=self.spacing)
        bench_label.grid(row=0, column=1, padx=self.spacing, pady=self.spacing)

        self.canvas_active.grid(row=1, column=0, sticky="nsew", padx=self.spacing, pady=self.spacing)
        self.canvas_bench.grid(row=1, column=1, sticky="nsew", padx=self.spacing, pady=self.spacing)
        
        # Bind mouse clicks to selection function
        self.canvas_active.bind("<Button-1>", lambda event: self.select_player(event, "active"))
        self.canvas_bench.bind("<Button-1>", lambda event: self.select_player(event, "bench"))

        # Make sure the columns and rows take up equal space
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        # Button to swap players
        swap_button = tk.Button(self.root, text="Wissel", command=self.wissel, font=("Helvetica", int(12 * self.scale_factor)))
        swap_button.pack(pady=self.spacing)

        # Button to end the game
        end_button = tk.Button(self.root, text="Einde", command=self.end, font=("Helvetica", int(12 * self.scale_factor)))
        end_button.pack(side='right', pady=self.spacing)

        # Button to pause the game
        pause_button = tk.Button(self.root, text="Pauze", command=self.pause, font=("Helvetica", int(12 * self.scale_factor)))
        pause_button.pack(side='right', pady=self.spacing)

        # Exit full screen on "Esc" key
        self.root.bind("<Escape>", lambda event: self.root.attributes("-fullscreen", False))

        # Initial display update and run the main loop
        self.refresh_dashboard()
        self.root.mainloop()

    def refresh_dashboard(self):
        """ Continuously refresh the dashboard every second """
        if not self.paused:
            self.create_display()  # Redraw the entire dashboard
        self.root.after(1000, self.refresh_dashboard)  # Schedule the next refresh after 1 second

    def create_display(self):
        # Remove all previous drawings
        self.canvas_active.delete("all")
        self.canvas_bench.delete("all")

        # Draw the players
        for speler in wedstrijd.spelers.index:
            if wedstrijd.spelers.at[speler,"Actief"]:
                width, height = self.ACTIVE_RECT_SIZE
                y_pos = self.spacing + wedstrijd.spelers.at[speler,"Spot"] * (height + self.spacing)
                self.canvas_active.create_rectangle(self.spacing, y_pos, self.spacing + width, y_pos + height, fill=self.ACTIVE_COLOR)
                self.canvas_active.create_text(self.spacing + width // 2, y_pos + height // 2, text=speler, font=("Helvetica", int(12*self.scale_factor)))
                tijd_op_het_veld = time.time() - wedstrijd.spelers.at[speler,"Laatste wijziging"]
                tijd_op_het_veld = time.strftime("%M:%S", time.gmtime(tijd_op_het_veld)) # format mm:ss
                self.canvas_active.create_text(self.spacing + 50, y_pos + height // 2, text=tijd_op_het_veld, font=("Helvetica", int(12*self.scale_factor)))
            else:
                width, height = self.BENCH_RECT_SIZE
                y_pos = self.spacing + wedstrijd.spelers.at[speler,"Spot"] * (height + self.spacing/2)
                self.canvas_bench.create_rectangle(self.spacing, y_pos, self.spacing + width, y_pos + height, fill=self.BENCH_COLOR)
                self.canvas_bench.create_text(self.spacing + width // 2, y_pos + height // 2, text=speler, font=("Helvetica", int(12*self.scale_factor)))
                tijd_op_de_bank = time.time() - wedstrijd.spelers.at[speler,"Laatste wijziging"]
                if tijd_op_de_bank < np.inf:
                    tijd_op_de_bank = time.strftime("%M:%S", time.gmtime(tijd_op_de_bank)) # format mm:ss
                gespeeld = time.strftime("%M:%S", time.gmtime(wedstrijd.spelers.loc[speler,'Gespeeld'])) # format mm:ss
                self.canvas_bench.create_text(self.spacing + 20, y_pos + height // 2, 
                                              text=f' Recuperatie: {tijd_op_de_bank} \n Gespeeld: {gespeeld}', 
                                              font=("Helvetica", int(12*self.scale_factor)), anchor='w')

    # Function to handle player swapping logic
    def wissel(self):
        if self.active_selection is not None and self.bench_selection is not None:
            wedstrijd.wissel(speler_uit = wedstrijd.spelers.loc[(wedstrijd.spelers['Actief']) & (wedstrijd.spelers['Spot'] == self.active_selection)].index[0], 
                             speler_in = wedstrijd.spelers.loc[~(wedstrijd.spelers['Actief']) & (wedstrijd.spelers['Spot'] == self.bench_selection)].index[0], 
                             tijdstip = time.time())
            # Swap between active and bench
            self.create_display()
            self.reset_selections()

    # Function to select a player when clicked
    def select_player(self, event, source):
        if source == "active":
            # Calculate index based on y-position clicked
            index = (event.y - self.spacing//2) // (self.ACTIVE_RECT_SIZE[1] + self.spacing)
            if 0 <= index <= wedstrijd.spelers.loc[wedstrijd.spelers["Actief"], 'Spot'].max():
                self.active_selection = index
                self.canvas_active.delete("active_selected")  # Remove previous highlight
                self.highlight_selection(self.canvas_active, self.active_selection, self.ACTIVE_RECT_SIZE, "active_selected", self.spacing)
        elif source == "bench":
            # Calculate index based on y-position clicked
            index = (event.y - self.spacing//2) // (self.BENCH_RECT_SIZE[1] + self.spacing/2)
            if 0 <= index <= wedstrijd.spelers.loc[~wedstrijd.spelers["Actief"], 'Spot'].max():
                self.bench_selection = index
                self.canvas_bench.delete("bench_selected")  # Remove previous highlight
                self.highlight_selection(self.canvas_bench, self.bench_selection, self.BENCH_RECT_SIZE, "bench_selected", self.spacing/2)

    # Function to highlight selected player with the appropriate tag
    def highlight_selection(self, canvas, index, rect_size, tag, spacing):
        width, height = rect_size
        y_pos = self.spacing + index * (height + spacing)
        canvas.create_rectangle(self.spacing, y_pos, self.spacing + width, y_pos + height, outline="red", width=2, tags=tag)

    # Reset selections after swapping
    def reset_selections(self):
        self.active_selection = None
        self.bench_selection = None
        self.canvas_active.delete("active_selected")
        self.canvas_bench.delete("bench_selected")

        # delete selection highlight
        self.canvas_active.delete("active_selected")
        self.canvas_bench.delete("bench_selected")
    
    def pause(self):
        tijdstip = time.time()
        self.paused = True

        def unpause():
            wedstrijd.add_pause(begin=tijdstip, einde=time.time())
            popup.destroy()
            self.paused = False
            self.create_display()
        
        def cancel():
            popup.destroy()
            self.paused = False
        
        # pop up window asking for confirmation
        popup = tk.Tk()
        popup.wm_title("Pauze")
        label = tk.Label(popup, text="De wedstrijd is gepauzeerd.", font=("Helvetica", int(12 * self.scale_factor)))
        label.pack(side="top", fill="x", pady=10)
        resume_button = tk.Button(popup, text="Wedstrijd hervatten", command=unpause, font=("Helvetica", int(12 * self.scale_factor)))
        resume_button.pack()
        cancel_button = tk.Button(popup, text="Pauze ongedaan maken", command=cancel, font=("Helvetica", int(12 * self.scale_factor)))
        cancel_button.pack()
        
    def end(self):
        tijdstip = time.time()

        def end_game():
            wedstrijd.end(tijdstip)
            # Close the dashboard
            self.root.destroy()
            self.root.quit()
        
        # pop up window asking for confirmation
        popup = tk.Tk()
        popup.wm_title("Einde wedstrijd")
        label = tk.Label(popup, text="Wedstrijd beëindigen?", font=("Helvetica", int(12 * self.scale_factor)))
        label.pack(side="top", fill="x", pady=10)
        yes_button = tk.Button(popup, text="Ja", command=end_game, font=("Helvetica", int(12 * self.scale_factor)))
        yes_button.pack()
        no_button = tk.Button(popup, text="Nee", command=popup.destroy, font=("Helvetica", int(12 * self.scale_factor)))
        no_button.pack()


# Example usage
alle_spelers = ["Speler 1", "Speler 2", "Speler 3", "Speler 4", "Speler 5", "Speler 6", "Speler 7", "Speler 8", "Speler 9", "Speler 10"]
wedstrijd = Wedstrijd(alle_spelers)
wedstrijd.init_opstelling("Speler 1", "Speler 2", "Speler 3", "Speler 4", "Speler 5")
wedstrijd.start(tijdstip=time.time())

dashboard = Dashboard()