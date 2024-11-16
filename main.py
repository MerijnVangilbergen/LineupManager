import tkinter as tk
import numpy as np
import pandas as pd
import time
import logging


time_ref = 4*60

def configure_grid_uniformly(root):
    # Make sure the columns and rows take up equal space
    for i in range(root.grid_size()[0]):
        root.grid_columnconfigure(i, weight=1)
    for i in range(root.grid_size()[1]):
        root.grid_rowconfigure(i, weight=1)

def flip_colour(button):
    current_color = button.cget("bg")  # Get current background color
    new_color = "green" if current_color == "red" else "red"  # Toggle color
    button.config(bg=new_color)

def health_to_colour(health:float, scale:str, low:str, high:str) -> str:
    if scale == "g-r":
        rgb = low + (high - low) * np.array([2*(1-health), 2*health, 0])
    elif scale == "b-r":
        rgb = low + (high - low) * np.array([2*(1-health), 0, 2*health])
    else:
        raise ValueError("Invalid scale. Should be 'g-r' or 'b-r'.")
    rgb = np.clip(np.asarray(rgb, dtype=int), low, high)
    hex = f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
    return hex


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
        self.spelers["Actief"] = np.append(np.ones(5, dtype=bool), np.zeros(len(spelers) - 5, dtype=bool))
        self.spelers["Spot"] = np.append(np.arange(5), np.arange(len(spelers) - 5))
        self.spelers["Gespeeld"] = 0.0
        self.spelers["Laatste wijziging"] = np.nan
    
    def log_function_call(self, function_name, *args):
        """Logs the function calls with their arguments."""
        logging.info(f'{function_name}({args})')

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
        if ~np.isnan(self.spelers.at[speler_uit, "Laatste wijziging"]):
            self.spelers.at[speler_uit, "Gespeeld"] += tijdstip - self.spelers.at[speler_uit, "Laatste wijziging"]
            self.spelers.at[speler_uit, "Laatste wijziging"] = tijdstip

        # van de bank
        self.spelers.at[speler_in, "Actief"] = True
        if ~np.isnan(self.spelers.at[speler_in, "Laatste wijziging"]):
            self.spelers.at[speler_in, "Laatste wijziging"] = tijdstip

        self.spelers.at[speler_in, 'Spot'], self.spelers.at[speler_uit, 'Spot'] = self.spelers.at[speler_uit, 'Spot'], self.spelers.at[speler_in, 'Spot']

        # order de bankspelers
        self.order_bench()

    def order_bench(self):
        # This function orders the bench players based on the time they have been active
        bench = self.spelers.loc[~self.spelers["Actief"]]
        argsort = bench['Gespeeld'].argsort()
        self.spelers.loc[bench.index[argsort], "Spot"] = np.arange(len(bench))


class PlayerSelector:
    def __init__(self, selectie=None):
        # Create main window
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)

        # Full screen toggle using esc and f keys
        self.root.bind("<Escape>", lambda event: self.root.attributes("-fullscreen", False))
        self.root.bind("f", lambda event: self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen")))
        
        # Keep track of sizes and spacing
        screen_size = np.asarray([self.root.winfo_screenwidth(), self.root.winfo_screenheight()], dtype=int)
        ncols = 4

        scale_factor = screen_size[1] / 1080  # Reference height is 1080px, adjust for others
        font = ("Helvetica", int(18*scale_factor))

        # Create a selection button for each player
        self.init_players(ncols=ncols, button_size=(30,4), font=font, selectie=selectie)

        # add the proceed button in a new row
        proceed_button = tk.Button(self.root, 
                                   text="Ga verder", 
                                   font=font, 
                                   width=60, 
                                   height=4, 
                                   command=self.ga_verder)
        proceed_button.grid(row=np.ceil(len(self.player_buttons) / ncols).astype(int), columnspan=ncols)

        configure_grid_uniformly(self.root)
        self.root.mainloop()

    def init_players(self, ncols:int, button_size:tuple|list|np.ndarray, font, selectie:list=None):
        spelers = np.loadtxt('spelers.txt', dtype=str, delimiter=',')
        if selectie is None:
            selected = np.ones(len(spelers), dtype=bool)
        else:
            selected = np.isin(spelers, selectie)

        self.player_buttons = []
        for ss, speler in enumerate(spelers):
            button = tk.Button( self.root, 
                                text=speler, 
                                font=font, 
                                width=button_size[0], 
                                height=button_size[1], 
                                relief=tk.FLAT, 
                                bg='green' if selected[ss] else 'red')
            button.config(command=lambda button=button: flip_colour(button))
            button.grid(row=ss // ncols, column=ss % ncols)
            self.player_buttons.append(button)

        configure_grid_uniformly(self.root)

    def ga_verder(self):
        # Capture the player selection and close the window
        self.selected_players = [button.cget("text") for button in self.player_buttons if button.cget("bg") == "green"]
        self.root.destroy()
        self.root.quit()


class Dashboard():
    def __init__(self):
        self.paused = False
        self.active_selection = None
        self.bench_selection = None

        # Create main window
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)
        screen_size = np.asarray([self.root.winfo_screenwidth(), self.root.winfo_screenheight()], dtype=int)
        scale_factor = screen_size[1] / 1080  # Reference height is 1080px, adjust for others
        self.font = ("Helvetica", int(14*scale_factor))

        # Full screen toggle using esc and f keys
        self.root.bind("<Escape>", lambda event: self.root.attributes("-fullscreen", False))
        self.root.bind("f", lambda event: self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen")))

        # Top ribbon
        # selection_button = tk.Button(self.root, text="Update selection", command=self.update_selection, font=self.font)
        # selection_button.pack(side='top', anchor='nw')

        # Configuration: Define sizes
        self.spacing = int(screen_size[1] * .04)  # Spacing between rectangles

        # Create a frame to organize the layout
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=5)
        main_frame.grid_rowconfigure(2, weight=1)

        # Create subtitles for active players and bench players
        field_label = tk.Label(main_frame, text="Het veld", font=self.font)
        bench_label = tk.Label(main_frame, text="De bank", font=self.font)
        field_label.grid(row=0, column=0)
        bench_label.grid(row=0, column=1)

        # The active players
        self.frame_active = tk.Frame(main_frame)
        self.frame_active.grid(row=1, column=0, sticky="nsew")
        self.field_buttons, self.field_labels = self.init_players(actief=True, frame=self.frame_active, size = (80,4))

        # The bench players
        self.frame_bench = tk.Frame(main_frame)
        self.frame_bench.grid(row=1, column=1, sticky="nsew")
        self.bench_buttons, self.bench_labels = self.init_players(actief=False, frame=self.frame_bench, size = (80,2))

        # Bottom frame
        bottom_frame = tk.Frame(main_frame)
        bottom_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")

        # Button to swap players
        swap_button = tk.Button(bottom_frame, text="Wissel", command=self.wissel, font=self.font, width=30, height=2)
        swap_button.grid(row=0, column=1)

        # Button to start the game
        self.start_stop_button = tk.Button(bottom_frame, text="Start wedstrijd", command=self.start, font=self.font, width=30, height=2)
        self.start_stop_button.grid(row=0, column=2)
        configure_grid_uniformly(bottom_frame)

        # Initial display update and run the main loop
        self.refresh_dashboard()
        self.root.mainloop()

    def init_players(self, actief:bool, frame:tk.Frame, size:tuple|list|np.ndarray):
        buttons = []
        labels = []
        spelers = wedstrijd.spelers.loc[wedstrijd.spelers["Actief"] == actief]
        for spot, name in zip(spelers["Spot"], spelers.index):
            player_frame = tk.Frame(frame)
            player_frame.grid(row=spot, column=0)
            button = tk.Button( player_frame, 
                                text=name, 
                                font=self.font, 
                                width=size[0], 
                                height=size[1], 
                                relief=tk.FLAT, 
                                command=lambda active=actief, spot=spot: self.select(active, spot))
            button.pack()
            buttons.append(button)

            label = tk.Label(player_frame, font=self.font, anchor='w')
            label.place(relx=.02, rely=.5, anchor='w')
            labels.append(label)
        configure_grid_uniformly(frame)
        return buttons, labels

    def refresh_dashboard(self):
        ''' Continuously refresh the dashboard every second '''
        if not self.paused:
            self.update_time_features()  # Redraw the entire dashboard
        self.root.after(1000, self.refresh_dashboard)  # Schedule the next refresh after 1 second

    def update_time_features(self):
        ''' Update all time dependent features: time labels and colours '''
        for speler, spot in zip(wedstrijd.spelers.index, wedstrijd.spelers['Spot']):
            if wedstrijd.spelers.at[speler,"Actief"]:
                tijd_op_het_veld = 0 if np.isnan(wedstrijd.spelers.at[speler,"Laatste wijziging"]) else time.time() - wedstrijd.spelers.at[speler,"Laatste wijziging"]
                health = 1 / (1 + (tijd_op_het_veld/time_ref)**2)
                colour = health_to_colour(health=health, scale="g-r", low=144, high=238)

                self.field_buttons[spot].config(bg=colour)
                self.field_labels[spot].config(bg=colour, text=time.strftime("%M:%S", time.gmtime(tijd_op_het_veld))) # format mm:ss
            else:
                tijd_op_de_bank = np.inf if np.isnan(wedstrijd.spelers.at[speler,"Laatste wijziging"]) else time.time() - wedstrijd.spelers.at[speler,"Laatste wijziging"]
                health = 1 - 1 / (1 + (tijd_op_de_bank/time_ref)**2)
                colour = health_to_colour(health=health, scale="g-r", low=200, high=238)

                if tijd_op_de_bank < np.inf:
                    tijd_op_de_bank = time.strftime("%M:%S", time.gmtime(tijd_op_de_bank)) # format mm:ss
                gespeeld = time.strftime("%M:%S", time.gmtime(wedstrijd.spelers.loc[speler,'Gespeeld'])) # format mm:ss

                self.bench_buttons[spot].config(bg=colour)
                self.bench_labels[spot].config(bg=colour, text=f'Recuperatie: {tijd_op_de_bank}\nGespeeld: {gespeeld}')
    
    def update_bench_names(self):
        inactief = wedstrijd.spelers.loc[~wedstrijd.spelers["Actief"]]
        for spot, name in zip(inactief["Spot"], inactief.index):
            self.bench_buttons[spot].config(text=name)

    # def update_selection(self):
    #     player_selector = PlayerSelector(wedstrijd.spelers.index)
    #     spelers = player_selector.selected_players
    #     pass

    # Function to handle player swapping logic
    def wissel(self):
        if self.active_selection is not None and self.bench_selection is not None:
            peler_uit = wedstrijd.spelers.loc[(wedstrijd.spelers['Actief']) & (wedstrijd.spelers['Spot'] == self.active_selection)].index[0]
            speler_in = wedstrijd.spelers.loc[~(wedstrijd.spelers['Actief']) & (wedstrijd.spelers['Spot'] == self.bench_selection)].index[0]
            wedstrijd.wissel(speler_uit = peler_uit, 
                             speler_in = speler_in, 
                             tijdstip = time.time())

            # interchange names
            self.field_buttons[self.active_selection].config(text=speler_in)
            self.update_bench_names() # all need to be updated as the bench was reordered
            self.update_time_features()

            # unselect both
            self.set_highlight(button=self.field_buttons[self.active_selection], highlight=False)
            self.set_highlight(button=self.bench_buttons[self.bench_selection], highlight=False)
            self.active_selection = None
            self.bench_selection = None

    # Function to select a player when clicked
    def select(self, active:bool, spot:int):
        if active:
            # Unhighlight the previous selection
            if self.active_selection is not None:
                self.set_highlight(button=self.field_buttons[self.active_selection], highlight=False)
            # Store the new selection
            if spot == self.active_selection:
                self.active_selection = None
            else:
                self.active_selection = spot
            # Highlight the new selection
            if self.active_selection is not None:
                self.set_highlight(button=self.field_buttons[spot], highlight=True)
        else:
            # Unhighlight the previous selection
            if self.bench_selection is not None:
                self.set_highlight(button=self.bench_buttons[self.bench_selection], highlight=False)
            # Store the new selection
            if spot == self.bench_selection:
                self.bench_selection = None
            else:
                self.bench_selection = spot
            # Highlight the new selection
            if self.bench_selection is not None:
                self.set_highlight(button=self.bench_buttons[spot], highlight=True)

    # Function to highlight selected player with the appropriate tag
    def set_highlight(self, button, highlight:bool):
        if highlight:
            button.config(relief=tk.SOLID)
        else:
            button.config(relief=tk.FLAT)

    # Reset selections after swapping
    def reset_selections(self):
        self.active_selection = None
        self.bench_selection = None
        # self.canvas_active.delete("active_selected")
        # self.canvas_bench.delete("bench_selected")

        # delete selection highlight
        # self.canvas_active.delete("active_selected")
        # self.canvas_bench.delete("bench_selected")
    
    def start(self):
        wedstrijd.start(time.time())

        # make the start button a pause button
        self.start_stop_button.config(text="Pauzeer / Beëindig wedstrijd", command=self.pause)

    def pause(self):
        tijdstip = time.time()
        self.paused = True

        def unpause():
            wedstrijd.add_pause(begin=tijdstip, einde=time.time())
            popup.destroy()
            self.paused = False
            self.update_time_features()
        
        def cancel():
            popup.destroy()
            self.paused = False
        
        # pop up window asking for confirmation
        popup = tk.Tk()
        popup.wm_title("Pauze")
        label = tk.Label(popup, text="De wedstrijd is gepauzeerd.", font=self.font)
        label.pack(side="top", fill="x", pady=10)
        resume_button = tk.Button(popup, text="Wedstrijd hervatten", command=unpause, font=self.font)
        resume_button.pack()
        cancel_button = tk.Button(popup, text="Pauze ongedaan maken", command=cancel, font=self.font)
        cancel_button.pack()
        cancel_button = tk.Button(popup, text="Wedstrijd beëindigen", command=lambda: self.end(tijdstip), font=self.font)
        cancel_button.pack()
        
    def end(self, tijdstip):
        def end_game():
            wedstrijd.end(tijdstip)
            self.root.destroy()
            self.root.quit()
        
        # pop up window asking for confirmation
        popup = tk.Tk()
        popup.wm_title("Einde wedstrijd")
        label = tk.Label(popup, text="Wedstrijd beëindigen?", font=self.font)
        label.pack(side="top", fill="x", pady=10)
        yes_button = tk.Button(popup, text="Ja", command=end_game, font=self.font)
        yes_button.pack()
        no_button = tk.Button(popup, text="Nee", command=popup.destroy, font=self.font)
        no_button.pack()


# Example usage
player_selector = PlayerSelector()
spelers = player_selector.selected_players

wedstrijd = Wedstrijd(spelers)
dashboard = Dashboard()