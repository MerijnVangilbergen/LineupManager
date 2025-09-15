import tkinter as tk
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from copy import deepcopy as copy
import time
from os.path import exists
from shutil import copyfile
from win32api import GetSystemMetrics


# Global variables
time_ref = 4*60
screen_size = np.array([GetSystemMetrics(0), GetSystemMetrics(1)], dtype=int)


# Preparation
if not exists('spelers.txt'):
    # create spelers.txt as copy of spelers_voorbeeld.txt
    copyfile('spelers_voorbeeld.txt', 'spelers.txt')
    print("---------------------------------------------------------")
    print("Please update the player names in the file 'spelers.txt'.")
    print("---------------------------------------------------------")
    print("Continuing with the default names.")


def configure_grid_uniformly(root):
    # Make sure the columns and rows take up equal space
    for i in range(root.grid_size()[0]):
        root.grid_columnconfigure(i, weight=1)
    for i in range(root.grid_size()[1]):
        root.grid_rowconfigure(i, weight=1)

def health_to_colour(health:float, low:str, high:str) -> str:
    rgb = low + (high - low) * np.array([2*(1-health), 2*health, 0])
    rgb = np.clip(np.asarray(rgb, dtype=int), low, high)
    hex = f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
    return hex

def time_to_string(t:float) -> str:
    # Convert time in seconds to a string in the format mm:ss (without leading zero).
    t = np.round(t)
    t_as_string = time.strftime("%M:%S", time.gmtime(t))
    if t_as_string[0] == '0':
        t_as_string = t_as_string[1:] # remove leading zero
    return t_as_string


class Wedstrijd:
    def __init__(self, spelers):
        # Create a history list to keep track of the game
        self.history = []
        with open("history.txt", "w") as file:
            file.write("")
    
        # Create a DataFrame to keep track of the players
        self.spelers = spelers
        # self.spelers["Richttijd"] = # replace NaN values
        # self.spelers["Richttijd"] *= (5*50 / self.spelers["Richttijd"].sum())
        self.spelers["Status"] = np.concatenate((5*["Actief"], (len(spelers)-5)*["Bank"]))
        self.spelers["Spot"] = np.concatenate((np.arange(5), np.arange(len(spelers)-5)))
        self.spelers["Gespeeld"] = 0.0
        self.spelers["Gespeeld%"] = 0.0
        self.spelers["Laatste wijziging"] = -np.inf
        
        self.paused = True
    
    def unpause(self, tijdstip):
        actieve_spelers = self.spelers.loc[self.spelers["Status"] == "Actief"].sort_values(by="Spot").index.values
        self.history.append(HistoryItem(type='unpause', time=tijdstip, spelers=actieve_spelers))
        self.paused = False
        self.spelers.loc[self.spelers["Status"] == "Actief", "Laatste wijziging"] = tijdstip

    def pause(self, tijdstip):
        self.history.append(HistoryItem(type='pause', time=tijdstip))
        self.paused = True
        self.spelers.loc[self.spelers["Status"] == "Actief", "Gespeeld"] += tijdstip - self.spelers.loc[self.spelers["Status"] == "Actief", "Laatste wijziging"]
        self.spelers.loc[self.spelers["Status"] == "Actief", "Laatste wijziging"] = tijdstip
    
    def wissel(self, speler_uit, speler_in, tijdstip):
        if not self.paused:
            self.history.append(HistoryItem(type='wissel', time=tijdstip, speler_uit=speler_uit, speler_in=speler_in))

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
        self.spelers["Gespeeld%"] = np.where(self.spelers["Richttijd"] > 0, self.spelers["Gespeeld"] / (60*self.spelers["Richttijd"]), 100 + self.spelers["Gespeeld"])
        bench = self.spelers.loc[self.spelers["Status"] == "Bank"]

        argsort = bench["Gespeeld%"].argsort()
        self.spelers.loc[bench.index[argsort], "Spot"] = np.arange(len(bench))

    def report(self, save=False):
        if not self.paused:
            self_ = copy(self)
            self_.pause(tijdstip=time.time())
            return self_.report(save=save)

        spelers = copy(self.spelers)
        spelers['Colour'] = plt.cm.tab20.colors[:len(spelers)]
        spelers['Speelbeurten_begin'] = [[] for _ in range(len(spelers))]
        spelers['Speelbeurten_einde'] = [[] for _ in range(len(spelers))]
        spelers.sort_values(by='Gespeeld', inplace=True)

        fig = plt.figure(dpi = 100 * screen_size[1] / 1080)
        manager = plt.get_current_fig_manager()
        manager.full_screen_toggle()

        def draw_bar(idx, speler, start, end):
            ax_history.barh(y = idx, 
                            left = start, 
                            width = end - start, 
                            label = speler, 
                            color = spelers.at[speler, 'Colour'])
            ax_history.text(x = (start + end)/2, 
                            y = idx, 
                            s = f'{speler}\n{time_to_string(end - start)}', 
                            ha = 'center', 
                            va = 'center', 
                            color = 'k')

        def verwijder_keeper_outliers(spelers):
            alle_speelduren = np.concatenate(spelers['Speelduren'].values)
            argmax = np.argmax(alle_speelduren)
            max1 = alle_speelduren[argmax]
            other = np.delete(alle_speelduren, argmax)
            argmax = np.argmax(other)
            max2 = other[argmax]
            other = np.delete(other, argmax)

            # Two outliers are expected from the goalkeeper. Remove them.
            mu, sigma = np.mean(other), np.std(other, ddof=1)
            if max2 > mu + 2*sigma:
                outlier = max2
            elif max1 > mu + 2*sigma:
                outlier = max1
            else:
                outlier = np.inf

            # remove outliers
            for speler in spelers.index:
                inliers = spelers.at[speler,'Speelduren'] < outlier
                if np.all(inliers):
                    continue
                spelers.at[speler,'Speelbeurten_begin'] = np.array(spelers.at[speler,'Speelbeurten_begin'])[inliers]
                spelers.at[speler,'Speelbeurten_einde'] = np.array(spelers.at[speler,'Speelbeurten_einde'])[inliers]
                spelers.at[speler,'Speelduren'] = spelers.at[speler,'Speelduren'][inliers]
                spelers.at[speler,'Gespeeld'] = np.sum(spelers.at[speler,'Speelduren'])

        def hbar_total_time_per_player(spelers, ax):
            ax.set_xlabel('Totale speeltijd per speler')
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: time_to_string(x)))
            ax.invert_yaxis()
            ax.yaxis.set_visible(False)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_visible(False)
            container = ax.barh(y = spelers.index, 
                                width = spelers['Gespeeld'], 
                                color = spelers['Colour'])
            ax.bar_label(container, labels=[f'{speler} - {time_to_string(gespeeld)}' for speler, gespeeld in zip(spelers.index, spelers['Gespeeld'])], label_type='center')

        def hist_playtimes_per_player(spelers, ax):
            ax.set_xlabel('Duur per speelbeurt')
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: time_to_string(x)))
            ax.yaxis.set_visible(False)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_visible(False)
            _,bins,_ = ax.hist(x = spelers['Speelduren'].values, 
                                color = spelers['Colour'], 
                                stacked=True, density=True)
            ax.set_xticks(bins) # Set the x-ticks at the bin edges

        def scatter_playdur_evolution(spelers, ax):
            ax.set_xlabel('Tijd')
            ax.set_ylabel('Duur speelbeurt')

            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: time.strftime("%Hh%M", time.gmtime(np.round(x)))))
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: time_to_string(y)))
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            for speler in spelers.index:
                ax.scatter( spelers.at[speler, 'Speelbeurten_begin'], 
                            spelers.at[speler, 'Speelduren'], 
                            color = spelers.at[speler, 'Colour'])

        gs = fig.add_gridspec(3,2)
        ax_history = fig.add_subplot(gs[0,:])
        ax_time_per_player = fig.add_subplot(gs[1:,0])
        ax_playdur_distr = fig.add_subplot(gs[1,1])
        ax_playdur_evolution = fig.add_subplot(gs[2,1])
        fig.tight_layout()

        ax_history.invert_yaxis()
        ax_history.set_xlim(self.history[0].time, self.history[-1].time)
        ax_history.axis('off')

        for HI in self.history:
            if HI.type == 'unpause':
                actieve_spelers = copy(HI.spelers)
                tijden = np.repeat(HI.time, len(actieve_spelers))
            elif HI.type == 'pause':
                for idx, speler in enumerate(actieve_spelers):
                    draw_bar(idx, speler, tijden[idx], HI.time)
                    spelers.at[speler, 'Speelbeurten_begin'].append(tijden[idx])
                    spelers.at[speler, 'Speelbeurten_einde'].append(HI.time)
            elif HI.type == 'wissel':
                speler = HI.speler_uit
                idx = int(np.argwhere(actieve_spelers == speler)[0][0])
                draw_bar(idx, speler, tijden[idx], HI.time)
                spelers.at[speler, 'Speelbeurten_begin'].append(tijden[idx])
                spelers.at[speler, 'Speelbeurten_einde'].append(HI.time)
                actieve_spelers[idx] = HI.speler_in
                tijden[idx] = HI.time

        spelers['Speelduren'] = [np.array(einde) - np.array(begin) for begin, einde in zip(spelers['Speelbeurten_begin'], spelers['Speelbeurten_einde'])]
        verwijder_keeper_outliers(spelers)
        spelers = spelers.loc[spelers['Gespeeld'] > 0]

        hbar_total_time_per_player(spelers=spelers, ax=ax_time_per_player)
        hist_playtimes_per_player(spelers, ax=ax_playdur_distr)
        scatter_playdur_evolution(spelers, ax=ax_playdur_evolution)

        if save:
            plt.show()
            fig.savefig('wedstrijdoverzicht.png')
        return fig


class Dashboard():
    def __init__(self):
        self.active_selection = None
        self.bench_selection = None
        self.absent_selection = None

        # Create main window
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)
        scale_factor = screen_size[1] / 1080  # Reference height is 1080px, adjust for others
        self.font = ("Helvetica", int(14*scale_factor))

        # Full screen toggle using esc and f keys
        self.root.bind("<Escape>", lambda event: self.root.attributes("-fullscreen", False))
        self.root.bind("f", lambda event: self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen")))

        # Initialize the main frame and the extra frames
        self.init_main_frame()
        self.init_extra_frame_left()
        self.init_extra_frame_right()

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

        # Buttons to open the extra frames
        self.open_left_button = tk.Button(self.main_frame, 
                                          text=">", font=self.font, 
                                          bg='lightgrey', relief=tk.FLAT, width=2, height=50, 
                                          command=lambda: self.extra_frame_left.lift())
        self.open_left_button.place(relx=0, rely=0.5, anchor='w')
        self.open_right_button = tk.Button(self.main_frame, text="<", font=self.font, 
                                           bg='lightgrey', relief=tk.FLAT, width=2, height=50, 
                                           command=lambda: self.extra_frame_right.lift())
        self.open_right_button.place(relx=1, rely=0.5, anchor='e')

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
        
        self.open_left_button.lift() # make sure the open button is on top
        self.open_right_button.lift() # make sure the open button is on top
    
    def init_extra_frame_left(self):
        # Extra frame to keep the absent players
        self.extra_frame_left = tk.Frame(self.root, bg='lightgrey')
        self.extra_frame_left.place(relx=0, rely=0, relwidth=.25, relheight=1, anchor='nw')
        self.extra_frame_left.grid_rowconfigure(0, weight=1)
        self.extra_frame_left.grid_rowconfigure(1, weight=5)
        self.extra_frame_left.grid_rowconfigure(2, weight=1)
        self.extra_frame_left.grid_columnconfigure(0, weight=1)

        # Label
        absent_label = tk.Label(self.extra_frame_left, text="Afwezig", font=self.font, bg='lightgrey')
        absent_label.grid(row=0, column=0, sticky="nsew")

        # Action buttons
        extra_left_bottom_frame = tk.Frame(self.extra_frame_left, bg='lightgrey')
        extra_left_bottom_frame.grid(row=2, column=0, sticky="nsew")
        swap_to_absent_button = tk.Button(extra_left_bottom_frame, 
                                          text="<=", font=self.font, 
                                          command=self.move_to_absent, 
                                          width=10, height=3)
        swap_to_absent_button.place(relx=.25, rely=.5, anchor='center')
        swap_to_bench_button = tk.Button(extra_left_bottom_frame, 
                                         text="=>", font=self.font,
                                         command=self.move_to_bench, 
                                         width=10, height=3)
        swap_to_bench_button.place(relx=.75, rely=.5, anchor='center')
        
        # Button to close this extra frame
        self.close_left_button = tk.Button(self.extra_frame_left, 
                                           text='<', font=self.font, 
                                           bg='lightgrey', relief=tk.GROOVE, width=2, height=50, 
                                           command=lambda: self.extra_frame_left.lower())
        self.close_left_button.place(relx=1, rely=0.5, anchor='e')

        # The absent players
        self.create_absent()

        self.extra_frame_left.lower()

    def init_extra_frame_right(self):
        # Extra frame to keep the absent players
        self.extra_frame_right = tk.Frame(self.root, bg='lightgrey')
        self.extra_frame_right.place(relx=1, rely=0, relwidth=.25, relheight=1, anchor='ne')
        self.extra_frame_right.grid_rowconfigure(0, weight=1)
        self.extra_frame_right.grid_rowconfigure(1, weight=5)
        self.extra_frame_right.grid_rowconfigure(2, weight=1)
        self.extra_frame_right.grid_columnconfigure(0, weight=1)

        # Label
        history_label = tk.Label(self.extra_frame_right, text="History", font=self.font, bg='lightgrey')
        history_label.grid(row=0, column=0, sticky="nsew")

        # Report button
        extra_right_bottom_frame = tk.Frame(self.extra_frame_right, bg='lightgrey')
        extra_right_bottom_frame.grid(row=2, column=0, sticky="nsew")
        history_report_button = tk.Button(extra_right_bottom_frame, 
                                          text="Open report", font=self.font, 
                                          width=10, height=3, 
                                          command=self.open_report)
        history_report_button.place(relx=.5, rely=.5, anchor='center')
        
        # Button to close this extra frame
        self.close_right_button = tk.Button(self.extra_frame_right, 
                                           text='>', font=self.font, 
                                           bg='lightgrey', relief=tk.GROOVE, width=2, height=50,
                                           command=lambda: self.extra_frame_right.lower())
        self.close_right_button.place(relx=0, rely=0.5, anchor='w')

        self.extra_frame_right.lower()

    def create_bench(self):
        if hasattr(self, 'frame_bench'):
            self.frame_bench.destroy()
        
        self.frame_bench = tk.Frame(self.main_frame)
        self.frame_bench.grid(row=1, column=1, sticky="nsew")
        height = 3 if wedstrijd.spelers["Status"].eq("Bank").sum() < 9 else 2
        self.bench_buttons, self.bench_labels = self.init_players(status="Bank", frame=self.frame_bench, size = (60,height))
        self.open_right_button.lift() # make sure the open button is on top

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
            t = time.time() - wedstrijd.spelers.at[speler,"Laatste wijziging"]
            if wedstrijd.spelers.at[speler,"Status"] == "Actief":
                if t == np.inf:
                    health = 1
                    text = ''
                elif wedstrijd.paused:
                    health = 1 - 1 / (1 + (t/time_ref)**2)
                    if wedstrijd.spelers.loc[speler,"Richttijd"] > 0:
                        text = f'Recuperatie: {time_to_string(t)}\nGespeeld: {time_to_string(wedstrijd.spelers.loc[speler,"Gespeeld"])} ({wedstrijd.spelers.loc[speler,"Gespeeld%"]:.0%})'
                    else:
                        text = f'Recuperatie: {time_to_string(t)}\nGespeeld: {time_to_string(wedstrijd.spelers.loc[speler,"Gespeeld"])}'
                else:
                    health = 1 / (1 + (t/time_ref)**2)
                    text = time_to_string(t)

                colour = health_to_colour(health=health, low=144, high=238)
                self.field_buttons[spot].config(bg=colour)
                self.field_labels[spot].config(bg=colour, text=text)
            elif wedstrijd.spelers.at[speler,"Status"] == "Bank":
                health = 1 - 1 / (1 + (t/time_ref)**2)
                if t == np.inf:
                    text = ''
                else:
                    if wedstrijd.spelers.loc[speler,"Richttijd"] > 0:
                        text = f'Recuperatie: {time_to_string(t)}\nGespeeld: {time_to_string(wedstrijd.spelers.loc[speler,"Gespeeld"])} ({wedstrijd.spelers.loc[speler,"Gespeeld%"]:.0%})'
                    else:
                        text = f'Recuperatie: {time_to_string(t)}\nGespeeld: {time_to_string(wedstrijd.spelers.loc[speler,"Gespeeld"])}'
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
            self.open_report()
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
        cancel_button = tk.Button(popup, text="Wedstrijd beëindigen", command=lambda: self.end(popup,tijdstip), font=self.font, width=25, height=2)
        cancel_button.pack()
        
    def end(self, popup, tijdstip):
        popup.destroy()
        
        def end_game():
            wedstrijd.pause(tijdstip)
            popup.destroy()
            self.root.destroy()
            self.root.quit()
        
        # pop up window asking for confirmation
        popup = tk.Tk()
        popup.wm_title("Einde wedstrijd")
        label = tk.Label(popup, text="Wedstrijd beëindigen?", font=self.font)
        label.pack(side="top", fill="x", pady=10)
        tk.Button(popup, text="Ja", command=end_game, font=self.font).pack()
        tk.Button(popup, text="Nee", command=popup.destroy, font=self.font).pack()

    def open_report(self):
        if wedstrijd.paused and wedstrijd.spelers["Gespeeld"].sum() == 0:
            return
        fig = wedstrijd.report()
        root = tk.Tk()
        root.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0")
        canvas = FigureCanvasTkAgg(fig, master=root)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        plt.close()


class HistoryItem:
    def __init__(self, type:str, time, spelers=None, speler_uit=None, speler_in=None):
        if type == 'unpause':
            assert (spelers is not None) and (speler_uit is None) and (speler_in is None)
            self.spelers = spelers
        elif type == 'pause':
            assert (spelers is None) and (speler_uit is None) and (speler_in is None)
        elif type == 'wissel':
            assert (spelers is None) and (speler_uit is not None) and (speler_in is not None)
            self.speler_uit = speler_uit
            self.speler_in = speler_in
        else:
            raise ValueError(f"Invalid type. Type should be 'Wissel', 'pause' or 'unpause', not {type}.")
        self.type = type
        self.time = time
        self.log()

    def log(self):
        with open("history.txt", "a") as file:
            datetime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.time))
            if self.type == 'unpause':
                file.write(f"{datetime}: unpause(spelers = {', '.join(self.spelers)})\n")
            elif self.type == 'pause':
                file.write(f"{datetime}: pause\n")
            elif self.type == 'wissel':
                file.write(f"{datetime}: wissel(speler_uit={self.speler_uit}, speler_in={self.speler_in})\n")


# Example usage
spelers = pd.read_csv('spelers.txt', index_col='Naam')
wedstrijd = Wedstrijd(spelers)
dashboard = Dashboard()
wedstrijd.report(save=True)