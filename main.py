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

def health_to_colour(health:float, low:str, high:str) -> str:
    rgb = low + (high - low) * np.array([2*(1-health), 2*health, 0])
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
        self.spelers["Status"] = np.concatenate((5*["Actief"], (len(spelers)-5)*["Bank"]))
        self.spelers["Spot"] = np.concatenate((np.arange(5), np.arange(len(spelers)-5)))
        self.spelers["Gespeeld"] = 0.0
        self.spelers["Laatste wijziging"] = -np.inf
        
        self.paused = True
    
    def log_function_call(self, function_name, *args):
        """Logs the function calls with their arguments."""
        logging.info(f'{function_name}({args})')
    
    def unpause(self, tijdstip):
        self.log_function_call("unpause", tijdstip)
        self.paused = False
        self.spelers.loc[self.spelers["Status"] == "Actief", "Laatste wijziging"] = tijdstip

    def pause(self, tijdstip):
        self.log_function_call("pause", tijdstip)
        self.paused = True
        self.spelers.loc[self.spelers["Status"] == "Actief", "Gespeeld"] += tijdstip - self.spelers.loc[self.spelers["Status"] == "Actief", "Laatste wijziging"]
        self.spelers.loc[self.spelers["Status"] == "Actief", "Laatste wijziging"] = tijdstip
    
    def end(self, tijdstip):
        self.log_function_call("end", tijdstip)
        self.spelers.loc[self.spelers["Status"] == "Actief", "Gespeeld"] += tijdstip - self.spelers.loc[self.spelers["Status"] == "Actief", "Laatste wijziging"]
        self.spelers["Laatste wijziging"] = tijdstip
        self.spelers["Gespeeld"] = [time.strftime("%M:%S", time.gmtime(tijd)) for tijd in self.spelers["Gespeeld"]] # format mm:ss
        self.spelers["Gespeeld"].to_csv('wedstrijdoverzicht.csv')

    def wissel(self, speler_uit, speler_in, tijdstip):
        self.log_function_call("wissel", speler_uit, speler_in, tijdstip)

        # naar de bank
        self.spelers.at[speler_uit, "Status"] = "Bank"
        if not self.paused:
            self.spelers.at[speler_uit, "Gespeeld"] += tijdstip - self.spelers.at[speler_uit, "Laatste wijziging"]
            self.spelers.at[speler_uit, "Laatste wijziging"] = tijdstip

        # van de bank
        self.spelers.at[speler_in, "Status"] = "Actief"
        if not self.paused:
            self.spelers.at[speler_in, "Laatste wijziging"] = tijdstip

        self.spelers.at[speler_in, 'Spot'], self.spelers.at[speler_uit, 'Spot'] = self.spelers.at[speler_uit, 'Spot'], self.spelers.at[speler_in, 'Spot']

        # order de bankspelers
        self.order_bench()

    def order_bench(self):
        # This function orders the bench players based on the time they have been active
        bench = self.spelers.loc[self.spelers["Status"] == "Bank"]
        argsort = bench["Gespeeld"].argsort()
        self.spelers.loc[bench.index[argsort], "Spot"] = np.arange(len(bench))


class Dashboard():
    def __init__(self):
        self.active_selection = None
        self.bench_selection = None
        self.absent_selection = None

        # Create main window
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)
        screen_size = np.asarray([self.root.winfo_screenwidth(), self.root.winfo_screenheight()], dtype=int)
        scale_factor = screen_size[1] / 1080  # Reference height is 1080px, adjust for others
        self.font = ("Helvetica", int(14*scale_factor))

        # Full screen toggle using esc and f keys
        self.root.bind("<Escape>", lambda event: self.root.attributes("-fullscreen", False))
        self.root.bind("f", lambda event: self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen")))

        # Initialize the main frame and the extra frame on the left
        self.init_main_frame()
        self.init_extra_frame_left()

        # Initial display update and run the main loop
        self.update_time_features()
        self.refresh_dashboard()
        self.root.mainloop()

    def init_main_frame(self):
        # Create a frame to organize the layout
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=5)
        self.main_frame.grid_rowconfigure(2, weight=1)

        # Create subtitles for active players and bench players
        field_label = tk.Label(self.main_frame, text="Het veld", font=self.font)
        bench_label = tk.Label(self.main_frame, text="De bank", font=self.font)
        field_label.grid(row=0, column=0)
        bench_label.grid(row=0, column=1)

        # The active players
        frame_active = tk.Frame(self.main_frame)
        frame_active.grid(row=1, column=0, sticky="nsew")
        self.field_buttons, self.field_labels = self.init_players(status="Actief", frame=frame_active, size = (70,4))

        # The bench players
        self.create_bench()

        # Bottom frame
        bottom_frame = tk.Frame(self.main_frame)
        bottom_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")

        # Button to swap players
        swap_button = tk.Button(bottom_frame, text="Wissel", command=self.wissel, font=self.font, width=30, height=2)
        swap_button.grid(row=0, column=1)

        # Button to start the game
        self.start_stop_button = tk.Button(bottom_frame, text="Start wedstrijd", command=self.unpause, font=self.font, width=30, height=2)
        self.start_stop_button.grid(row=0, column=2)
        configure_grid_uniformly(bottom_frame)
        
        # Button to open the extra frame on the left
        self.open_left_button = tk.Button(self.main_frame, text=">", bg='lightgrey', command=lambda: self.extra_frame_left.lift(), font=self.font, width=2, height=50)
        self.open_left_button.place(relx=0, rely=0.5, anchor='w')
    
    def init_extra_frame_left(self):
        # Extra frame to keep the absent players
        self.extra_frame_left = tk.Frame(self.root, bg='lightgrey')
        self.extra_frame_left.place(relx=0, rely=0, relwidth=.25, relheight=1, anchor='nw')
        self.extra_frame_left.grid_rowconfigure(0, weight=1)
        self.extra_frame_left.grid_rowconfigure(1, weight=5)
        self.extra_frame_left.grid_rowconfigure(2, weight=1)
        self.extra_frame_left.grid_columnconfigure(0, weight=1)

        # Button to close this extra frame
        self.close_left_button = tk.Button(self.extra_frame_left, 
                                           text="<", font=self.font, 
                                           bg='lightgrey', 
                                           command=lambda: self.extra_frame_left.lower(), 
                                           width=2, height=50)
        self.close_left_button.place(relx=1, rely=0.5, anchor='e')

        # Label
        absent_label = tk.Label(self.extra_frame_left, text="Afwezig", font=self.font, bg='lightgrey')
        absent_label.grid(row=0, column=0, sticky="nsew")

        # The absent players
        self.create_absent()

        # Action buttons
        extra_bottom_frame = tk.Frame(self.extra_frame_left, bg='lightgrey')
        extra_bottom_frame.grid(row=2, column=0, sticky="nsew")
        swap_to_open_left_button = tk.Button(extra_bottom_frame, 
                                             text="<=", font=self.font, 
                                             command=self.move_to_absent, 
                                             width=10, height=3)
        swap_to_open_left_button.place(relx=.25, rely=.5, anchor='center')
        swap_to_bench_button = tk.Button(extra_bottom_frame, 
                                         text="=>", font=self.font,
                                         command=self.move_to_bench, 
                                         width=10, height=3)
        swap_to_bench_button.place(relx=.75, rely=.5, anchor='center')
        
        self.extra_frame_left.lower()

    def create_bench(self):
        if hasattr(self, 'frame_bench'):
            self.frame_bench.destroy()
        
        self.frame_bench = tk.Frame(self.main_frame)
        self.frame_bench.grid(row=1, column=1, sticky="nsew")
        height = 3 if wedstrijd.spelers["Status"].eq("Bank").sum() < 9 else 2
        self.bench_buttons, self.bench_labels = self.init_players(status="Bank", frame=self.frame_bench, size = (60,height))

    def create_absent(self):
        if hasattr(self, 'frame_absent'):
            self.frame_absent.destroy

        self.frame_absent = tk.Frame(self.extra_frame_left, bg='lightgrey')
        self.frame_absent.grid(row=1, column=0, sticky="nsew")
        self.absent_buttons = self.init_players(status="Afwezig", frame=self.frame_absent, size = (30,2))
        self.close_left_button.lift() # make sure the close button is on top

    def init_players(self, status:str, frame:tk.Frame, size:tuple):
        buttons = []
        labels = []
        spelers = wedstrijd.spelers.loc[wedstrijd.spelers["Status"] == status].sort_values(by="Spot")
        for spot, name in zip(spelers["Spot"], spelers.index):
            player_frame = tk.Frame(frame)
            player_frame.grid(row=spot, column=0)
            button = tk.Button( player_frame, 
                                text=name, 
                                font=self.font, 
                                bg='grey', 
                                width=size[0], 
                                height=size[1], 
                                relief=tk.FLAT, 
                                command=lambda status=status, spot=spot: self.select(status, spot))
            button.pack(expand=True, fill=tk.BOTH)
            buttons.append(button)

            if status != "Afwezig":
                label = tk.Label(player_frame, font=self.font, anchor='w')
                label.place(relx=.02, rely=.5, anchor='w')
                labels.append(label)
        configure_grid_uniformly(frame)

        if status == "Afwezig":
            return buttons
        else:
            return buttons, labels

    def refresh_dashboard(self):
        ''' Continuously refresh the dashboard every second '''
        self.update_time_features()
        self.root.after(1000, self.refresh_dashboard)  # Schedule the next refresh after 1 second

    def update_time_features(self):
        ''' Update all time dependent features: time labels and colours '''
        for speler, spot in zip(wedstrijd.spelers.index, wedstrijd.spelers['Spot']):
            if wedstrijd.spelers.at[speler,"Status"] == "Actief":
                if wedstrijd.spelers.at[speler,"Laatste wijziging"] == -np.inf:
                    health = 1
                    text = ''
                elif wedstrijd.paused:
                    tijd_op_de_bank = time.time() - wedstrijd.spelers.at[speler,"Laatste wijziging"]
                    health = 1 - 1 / (1 + (tijd_op_de_bank/time_ref)**2)
                    tijd_op_de_bank = time.strftime("%M:%S", time.gmtime(tijd_op_de_bank)) # format mm:ss
                    gespeeld = time.strftime("%M:%S", time.gmtime(wedstrijd.spelers.loc[speler,"Gespeeld"])) # format mm:ss
                    text = f'Recuperatie: {tijd_op_de_bank}\nGespeeld: {gespeeld}'
                else:
                    tijd_op_het_veld = time.time() - wedstrijd.spelers.at[speler,"Laatste wijziging"]
                    health = 1 / (1 + (tijd_op_het_veld/time_ref)**2)
                    text = time.strftime("%M:%S", time.gmtime(tijd_op_het_veld)) # format mm:ss

                colour = health_to_colour(health=health, low=144, high=238)
                self.field_buttons[spot].config(bg=colour)
                self.field_labels[spot].config(bg=colour, text=text)
            elif wedstrijd.spelers.at[speler,"Status"] == "Bank":
                if wedstrijd.spelers.at[speler,"Laatste wijziging"] == -np.inf:
                    health = 1
                    text = ''
                else:
                    tijd_op_de_bank = time.time() - wedstrijd.spelers.at[speler,"Laatste wijziging"]
                    health = 1 - 1 / (1 + (tijd_op_de_bank/time_ref)**2)
                    tijd_op_de_bank = time.strftime("%M:%S", time.gmtime(tijd_op_de_bank)) # format mm:ss
                    gespeeld = time.strftime("%M:%S", time.gmtime(wedstrijd.spelers.loc[speler,"Gespeeld"])) # format mm:ss
                    text = f'Recuperatie: {tijd_op_de_bank}\nGespeeld: {gespeeld}'

                colour = health_to_colour(health=health, low=200, high=238)
                self.bench_buttons[spot].config(bg=colour)
                self.bench_labels[spot].config(bg=colour, text=text)
    
    def update_bench_names(self):
        inactief = wedstrijd.spelers.loc[wedstrijd.spelers["Status"] == "Bank"]
        for spot, name in zip(inactief["Spot"], inactief.index):
            self.bench_buttons[spot].config(text=name)

    # Function to handle player swapping logic
    def wissel(self):
        if self.active_selection is not None and self.bench_selection is not None:
            speler_uit = wedstrijd.spelers.loc[(wedstrijd.spelers["Status"] == "Actief") & (wedstrijd.spelers['Spot'] == self.active_selection)].index[0]
            speler_in = wedstrijd.spelers.loc[(wedstrijd.spelers["Status"] == "Bank") & (wedstrijd.spelers['Spot'] == self.bench_selection)].index[0]
            wedstrijd.wissel(speler_uit = speler_uit, 
                             speler_in = speler_in, 
                             tijdstip = time.time())

            # interchange names
            self.field_buttons[self.active_selection].config(text=speler_in)
            self.update_bench_names() # all need to be updated as the bench was reordered
            self.update_time_features()

            # unselect both
            self.reset_selections()
    
    def move_to_absent(self):
        speler_mask = (wedstrijd.spelers["Status"] == "Bank") & (wedstrijd.spelers['Spot'] == self.bench_selection)

        wedstrijd.spelers.loc[speler_mask, "Status"] = "Afwezig"
        wedstrijd.spelers.loc[speler_mask, "Spot"] = len(self.absent_buttons)
        wedstrijd.spelers.loc[(wedstrijd.spelers["Status"] == "Bank") & (wedstrijd.spelers["Spot"] > self.bench_selection), "Spot"] -= 1
        self.reset_selections()
        self.create_bench()
        self.create_absent()
        self.update_time_features()

    def move_to_bench(self):
        speler_mask = (wedstrijd.spelers["Status"] == "Afwezig") & (wedstrijd.spelers['Spot'] == self.absent_selection)

        wedstrijd.spelers.loc[speler_mask, "Status"] = "Bank"
        wedstrijd.order_bench()
        wedstrijd.spelers.loc[(wedstrijd.spelers["Status"] == "Afwezig") & (wedstrijd.spelers["Spot"] > self.absent_selection), "Spot"] -= 1
        self.reset_selections()
        self.create_bench()
        self.create_absent()
        self.update_time_features()

    # Function to select a player when clicked
    def select(self, status:str, spot:int):
        if status == "Actief":
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
        elif status == "Bank":
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
        elif status == "Afwezig":
            # Unhighlight the previous selection
            if self.absent_selection is not None:
                self.set_highlight(button=self.absent_buttons[self.absent_selection], highlight=False)
            # Store the new selection
            if spot == self.absent_selection:
                self.absent_selection = None
            else:
                self.absent_selection = spot
            # Highlight the new selection
            if self.absent_selection is not None:
                self.set_highlight(button=self.absent_buttons[spot], highlight=True)

    # Function to highlight selected player with the appropriate tag
    def set_highlight(self, button, highlight:bool):
        if highlight:
            button.config(relief=tk.SOLID)
        else:
            button.config(relief=tk.FLAT)

    # Reset selections after swapping
    def reset_selections(self):
        if self.active_selection is not None:
            self.set_highlight(button=self.field_buttons[self.active_selection], highlight=False)
            self.active_selection = None
        if self.bench_selection is not None:
            self.set_highlight(button=self.bench_buttons[self.bench_selection], highlight=False)
            self.bench_selection = None
        if self.absent_selection is not None:
            self.set_highlight(button=self.absent_buttons[self.absent_selection], highlight=False)
            self.absent_selection = None

    def unpause(self):
        wedstrijd.unpause(time.time())
        self.update_time_features()

        # make the start button a pause button
        self.start_stop_button.config(text="Pauzeer / Beëindig wedstrijd", command=self.pause)

    def pause(self):
        tijdstip = time.time()

        def _pause():
            wedstrijd.pause(tijdstip)
            self.update_time_features()
            popup.destroy()
            
            # make the pause button a start button
            self.start_stop_button.config(text="Hervat wedstrijd", command=self.unpause)
        
        def _cancel():
            popup.destroy()
        
        # pop up window asking for confirmation
        popup = tk.Tk()
        popup.wm_title("Pauze")
        label = tk.Label(popup, text="De wedstrijd is gepauzeerd.", font=self.font)
        label.pack(side="top", fill="x", pady=10)
        resume_button = tk.Button(popup, text="Bevestigen", command=_pause, font=self.font, width=25, height=2)
        resume_button.pack()
        cancel_button = tk.Button(popup, text="Pauze ongedaan maken", command=_cancel, font=self.font, width=25, height=2)
        cancel_button.pack()
        cancel_button = tk.Button(popup, text="Wedstrijd beëindigen", command=lambda: self.end(tijdstip), font=self.font, width=25, height=2)
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
spelers = np.loadtxt('spelers.txt', dtype=str, delimiter=',')
wedstrijd = Wedstrijd(spelers)
dashboard = Dashboard()