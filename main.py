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

def get_coords(canvas, rectangle, coords:str) -> tuple:
    x0, y0, x1, y1 = canvas.coords(rectangle)
    if coords == 'center':
        return (int((x0 + x1) // 2), int((y0 + y1) // 2))
    elif coords == 'w':
        return (x0, int((y0 + y1) // 2))
    else:
        raise ValueError("Invalid coords.")

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
        self.spelers["Actief"] = False
        self.spelers["Spot"] = 0
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
    def __init__(self, spelers:list):
        # Create main window
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)

        # Full screen toggle using esc and f keys
        self.root.bind("<Escape>", lambda event: self.root.attributes("-fullscreen", False))
        self.root.bind("f", lambda event: self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen")))
        
        # Keep track of sizes and spacing
        screen_size = np.asarray([self.root.winfo_screenwidth(), self.root.winfo_screenheight()], dtype=int)
        ncols = 3
        grid_size = np.asarray([ncols, np.ceil(len(spelers)/ncols)], dtype=int)
        rect_size = np.asarray(.75 * screen_size / grid_size, dtype=int)

        scale_factor = screen_size[1] / 1080  # Reference height is 1080px, adjust for others
        self.font = ("Helvetica", int(12*scale_factor))

        # Create a selection button for each player
        def create_player_button(speler, ss):
            button = tk.Button(self.root, 
                               text=speler, 
                               font=self.font, 
                               width=rect_size[0], height=rect_size[1], 
                               bg='green')
            button.config(command=lambda button=button: flip_colour(button))
            button.grid(row=ss // 3, column=ss % 3)
            return button

        self.player_buttons = [create_player_button(speler, ss) for ss, speler in enumerate(spelers)]

        # add an extra row for the proceed button
        proceed_button = tk.Button(self.root, text="Ga verder", font=self.font, width=rect_size[0], height=rect_size[1], command=self.ga_verder)
        proceed_button.grid(row=grid_size[1], columnspan=grid_size[0])

        configure_grid_uniformly(self.root)
        self.root.mainloop()

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
        # self.active_rectangles = [None] * wedstrijd.spelers["Actief"].sum()
        # self.bench_rectangles = [None] * (~wedstrijd.spelers["Actief"]).sum()

        # Create main window
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)
        screen_size = np.asarray([self.root.winfo_screenwidth(), self.root.winfo_screenheight()], dtype=int)
        scale_factor = screen_size[1] / 1080  # Reference height is 1080px, adjust for others
        self.font = ("Helvetica", int(12*scale_factor))

        # Full screen toggle using esc and f keys
        self.root.bind("<Escape>", lambda event: self.root.attributes("-fullscreen", False))
        self.root.bind("f", lambda event: self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen")))

        # Configuration: Define sizes
        self.ACTIVE_RECT_SIZE = (int(screen_size[0] * .4), int(screen_size[1] * .075))  # Active player rectangles
        self.BENCH_RECT_SIZE = (int(screen_size[0] * .4), int(screen_size[1] * .045))  # Bench player rectangles
        self.spacing = int(screen_size[1] * .04)  # Spacing between rectangles

        # Create a frame to organize the layout
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create subtitles for active players and bench players
        active_label = tk.Label(main_frame, text="Het veld", font=self.font)
        bench_label = tk.Label(main_frame, text="De bank", font=self.font)
        active_label.grid(row=0, column=0, padx=self.spacing, pady=self.spacing)
        bench_label.grid(row=0, column=1, padx=self.spacing, pady=self.spacing)

        # Create canvases for active and bench players inside the frame
        self.canvas_active = tk.Canvas(main_frame)
        self.canvas_bench = tk.Canvas(main_frame)
        self.canvas_active.grid(row=1, column=0, sticky="nsew", padx=self.spacing, pady=self.spacing)
        self.canvas_bench.grid(row=1, column=1, sticky="nsew", padx=self.spacing, pady=self.spacing)
        
        # Bind mouse clicks to selection function
        self.canvas_active.bind("<Button-1>", lambda event: self.select_player(event, "active"))
        self.canvas_bench.bind("<Button-1>", lambda event: self.select_player(event, "bench"))

        # Make sure the columns and rows take up equal space
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        
        # Button to swap players
        swap_button = tk.Button(self.root, text="Wissel", command=self.wissel, font=self.font)
        swap_button.pack(pady=self.spacing)

        # Button to start the game
        self.start_stop_button = tk.Button(self.root, text="Start wedstrijd", command=self.start, font=self.font)
        self.start_stop_button.pack(side='right', pady=self.spacing)

        # Initial display update and run the main loop
        self.refresh_dashboard()
        self.root.mainloop()

    def refresh_dashboard(self):
        ''' Continuously refresh the dashboard every second '''
        if not self.paused:
            self.create_display()  # Redraw the entire dashboard
        self.root.after(1000, self.refresh_dashboard)  # Schedule the next refresh after 1 second

    def create_display(self):
        # Remove all previous drawings
        self.canvas_active.delete("all")
        self.canvas_bench.delete("all")

        # self.active_rectangles = [None] * wedstrijd.spelers["Actief"].sum()
        # self.bench_rectangles = [None] * (~wedstrijd.spelers["Actief"]).sum()
        
        # Draw the players
        for speler in wedstrijd.spelers.index:
            if wedstrijd.spelers.at[speler,"Actief"]:
                if np.isnan(wedstrijd.spelers.at[speler,"Laatste wijziging"]):
                    tijd_op_het_veld = 0
                else:
                    tijd_op_het_veld = time.time() - wedstrijd.spelers.at[speler,"Laatste wijziging"]
                health = 1 / (1 + (tijd_op_het_veld/time_ref)**2)
                colour = health_to_colour(health=health, scale="g-r", low=144, high=238)

                spot = wedstrijd.spelers.at[speler,"Spot"]
                xy = np.asarray([self.spacing, self.spacing + spot * (self.ACTIVE_RECT_SIZE[1] + self.spacing)], dtype=int)
                rectangle = self.canvas_active.create_rectangle(*xy, *(xy+self.ACTIVE_RECT_SIZE), fill=colour)
                # self.active_rectangles[spot] = rectangle
                self.canvas_active.create_text( get_coords(self.canvas_active, rectangle, 'center'), 
                                                text=speler, 
                                                font=self.font)
                self.canvas_active.create_text( get_coords(self.canvas_active, rectangle, 'w'), 
                                                anchor='w', 
                                                text=5*' ' + time.strftime("%M:%S", time.gmtime(tijd_op_het_veld)), # format mm:ss
                                                font=self.font)
            else:
                if np.isnan(wedstrijd.spelers.at[speler,"Laatste wijziging"]):
                    tijd_op_de_bank = np.inf
                else:
                    tijd_op_de_bank = time.time() - wedstrijd.spelers.at[speler,"Laatste wijziging"]
                health = 1 - 1 / (1 + (tijd_op_de_bank/time_ref)**2)
                colour = health_to_colour(health=health, scale="g-r", low=200, high=238)

                spot = wedstrijd.spelers.at[speler,"Spot"]
                xy = np.asarray([self.spacing, self.spacing + spot * (self.BENCH_RECT_SIZE[1] + self.spacing/2)], dtype=int)
                rectangle = self.canvas_bench.create_rectangle(*xy, *(xy+self.BENCH_RECT_SIZE), fill=colour)
                # self.bench_rectangles[spot] = rectangle
                self.canvas_bench.create_text(  get_coords(self.canvas_bench, rectangle, 'center'), 
                                                text=speler, 
                                                font=self.font)
                if tijd_op_de_bank < np.inf:
                    tijd_op_de_bank = time.strftime("%M:%S", time.gmtime(tijd_op_de_bank)) # format mm:ss
                gespeeld = time.strftime("%M:%S", time.gmtime(wedstrijd.spelers.loc[speler,'Gespeeld'])) # format mm:ss
                self.canvas_bench.create_text(  get_coords(self.canvas_bench, rectangle, 'w'), 
                                                anchor='w',
                                                text=f'  Recuperatie: {tijd_op_de_bank}\n  Gespeeld: {gespeeld}', 
                                                font=self.font)

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
        y_pos = self.spacing + index * (rect_size[1] + spacing)
        xy = np.asarray([self.spacing, y_pos], dtype=int)
        canvas.create_rectangle(*xy, *(xy+rect_size), outline="red", width=2, tags=tag)

    # Reset selections after swapping
    def reset_selections(self):
        self.active_selection = None
        self.bench_selection = None
        self.canvas_active.delete("active_selected")
        self.canvas_bench.delete("bench_selected")

        # delete selection highlight
        self.canvas_active.delete("active_selected")
        self.canvas_bench.delete("bench_selected")
    
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
            self.create_display()
        
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
alle_spelers = np.loadtxt('spelers.txt', dtype=str, delimiter=',')
player_selector = PlayerSelector(alle_spelers)
spelers = player_selector.selected_players

wedstrijd = Wedstrijd(spelers)
wedstrijd.init_opstelling(*spelers[:5])

dashboard = Dashboard()