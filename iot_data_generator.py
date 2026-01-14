"""
IoT Data Generator Application
Generates artificial IoT sensor data with visualization capabilities
"""
import warnings
warnings.filterwarnings("ignore", message=".*No wx.App created yet.*")

# GUI Framework
import wx
import wx.grid

# Data Processing
import pandas as pd
import numpy as np

# Visualization
import matplotlib.pyplot as plt
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas

# Data Generation
from faker import Faker

# Utilities
import json
import csv
import random
import threading
import time
from datetime import datetime, timedelta
from collections import Counter

fake = Faker()

class IoTDataGenerator:
    @staticmethod
    def generate_user_data(num_users=1000):
        """Generate user records"""
        users = []
        for _ in range(num_users):
            firstname = fake.first_name()
            lastname = fake.last_name()
            age = random.randint(18, 80)
            gender = random.choice(['Male', 'Female'])
            username = fake.user_name()
            address = fake.address().replace('\n', ', ')
            email = fake.email()
            
            users.append({
                'firstname': firstname,
                'lastname': lastname,
                'age': age,
                'gender': gender,
                'username': username,
                'address': address,
                'email': email,
                'sensor_data': []
            })
        return users
    
    @staticmethod
    def generate_sensor_data_for_user(start_date='2015-01-01', num_records=1000):
        """Generate sensor data for a single user"""
        sensor_data = []
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        
        # Generate data every 6 hours
        for _ in range(num_records):
            date_str = current_date.strftime('%Y-%m-%d')
            time_str = current_date.strftime('%H:%M:%S')
            
            # Outside temperature (70-95)
            outside_temp = random.uniform(70, 95)
            
            # Room temperature (0-10 degrees less than outside)
            temp_diff = random.uniform(0, 10)
            room_temp = outside_temp - temp_diff
            
            # Outside humidity (50-95)
            outside_humidity = random.uniform(50, 95)
            
            # Room humidity (0-10 degrees less than outside)
            humidity_diff = random.uniform(0, 10)
            room_humidity = outside_humidity - humidity_diff
            
            sensor_data.append({
                'date': date_str,
                'time': time_str,
                'outside_temperature': round(outside_temp, 2),
                'outside_humidity': round(outside_humidity, 2),
                'room_temperature': round(room_temp, 2),
                'room_humidity': round(room_humidity, 2)
            })
            
            # Increment by 6 hours
            current_date += timedelta(hours=6)
        
        return sensor_data

class StatisticsDialog(wx.Dialog):
    def __init__(self, parent, data):
        wx.Dialog.__init__(self, parent, title="Descriptive Statistics", size=(600, 400))
        
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Create text control for displaying statistics
        self.text_ctrl = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        vbox.Add(self.text_ctrl, proportion=1, flag=wx.EXPAND | wx.ALL, border=10)
        
        # Close button
        close_btn = wx.Button(panel, label="Close")
        close_btn.Bind(wx.EVT_BUTTON, self.on_close)
        vbox.Add(close_btn, flag=wx.ALIGN_CENTER | wx.BOTTOM, border=10)
        
        panel.SetSizer(vbox)
        self.generate_statistics(data)
    
    def generate_statistics(self, data):
        """Generate descriptive statistics from the data"""
        stats_text = "DESCRIPTIVE STATISTICS\n"
        stats_text += "=" * 50 + "\n\n"
        
        if not data:
            stats_text += "No data available. Please generate IoT data first."
            self.text_ctrl.SetValue(stats_text)
            return
        
        # Extract all sensor data
        all_sensor_data = []
        for user in data:
            all_sensor_data.extend(user['sensor_data'])
        
        if not all_sensor_data:
            stats_text += "No sensor data available."
            self.text_ctrl.SetValue(stats_text)
            return
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(all_sensor_data)
        
        # Statistics for each column
        columns = ['outside_temperature', 'outside_humidity', 'room_temperature', 'room_humidity']
        
        for col in columns:
            stats_text += f"\n{col.upper().replace('_', ' ')}:\n"
            stats_text += "-" * 30 + "\n"
            stats_text += f"Count: {len(df[col]):,}\n"
            stats_text += f"Mean: {df[col].mean():.2f}\n"
            stats_text += f"Std Dev: {df[col].std():.2f}\n"
            stats_text += f"Min: {df[col].min():.2f}\n"
            stats_text += f"25%: {df[col].quantile(0.25):.2f}\n"
            stats_text += f"50% (Median): {df[col].median():.2f}\n"
            stats_text += f"75%: {df[col].quantile(0.75):.2f}\n"
            stats_text += f"Max: {df[col].max():.2f}\n"
        
        # Additional statistics
        stats_text += "\n\nADDITIONAL STATISTICS\n"
        stats_text += "-" * 50 + "\n"
        stats_text += f"Total Users: {len(data):,}\n"
        stats_text += f"Total Sensor Records: {len(all_sensor_data):,}\n"
        stats_text += f"Date Range: {all_sensor_data[0]['date']} to {all_sensor_data[-1]['date']}\n"
        
        self.text_ctrl.SetValue(stats_text)
    
    def on_close(self, event):
        self.Destroy()

class PlotFrame(wx.Frame):
    def __init__(self, parent, title, data, plot_type):
        wx.Frame.__init__(self, parent, title=title, size=(1000, 800))
        
        self.data = data
        self.plot_type = plot_type
        self.plot_ready = False
        self.zoom_level = 1.0  # Current zoom level (1.0 = 100%)
        self.original_figsize = (12, 9)  # Store original figure size
        
        # Create a panel with scrollbars
        panel = wx.Panel(self)
        
        # Create a scrolled window for the plot area
        self.scrolled_window = wx.ScrolledWindow(panel)
        self.scrolled_window.SetScrollRate(20, 20)  # Set scroll speed
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Create toolbar panel for zoom controls (outside scrolled area)
        toolbar_panel = wx.Panel(panel)
        toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Zoom out button
        zoom_out_btn = wx.Button(toolbar_panel, label="−", size=(40, 30))
        zoom_out_btn.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        zoom_out_btn.Bind(wx.EVT_BUTTON, self.on_zoom_out)
        toolbar_sizer.Add(zoom_out_btn, 0, wx.ALL, 5)
        
        # Zoom level display
        self.zoom_label = wx.StaticText(toolbar_panel, label="100%")
        self.zoom_label.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        toolbar_sizer.Add(self.zoom_label, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        
        # Zoom in button
        zoom_in_btn = wx.Button(toolbar_panel, label="+", size=(40, 30))
        zoom_in_btn.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        zoom_in_btn.Bind(wx.EVT_BUTTON, self.on_zoom_in)
        toolbar_sizer.Add(zoom_in_btn, 0, wx.ALL, 5)
        
        # Reset zoom button
        reset_btn = wx.Button(toolbar_panel, label="Reset Zoom", size=(100, 30))
        reset_btn.Bind(wx.EVT_BUTTON, self.on_reset_zoom)
        toolbar_sizer.Add(reset_btn, 0, wx.ALL, 5)
        
        # Auto-fit button
        autofit_btn = wx.Button(toolbar_panel, label="Auto-Fit", size=(100, 30))
        autofit_btn.Bind(wx.EVT_BUTTON, self.on_autofit)
        toolbar_sizer.Add(autofit_btn, 0, wx.ALL, 5)
        
        # Add spacer
        toolbar_sizer.AddStretchSpacer(1)
        
        # Save plot button
        save_btn = wx.Button(toolbar_panel, label="Save Plot", size=(100, 30))
        save_btn.Bind(wx.EVT_BUTTON, self.on_save_plot)
        toolbar_sizer.Add(save_btn, 0, wx.ALL, 5)
        
        # Close button
        close_btn = wx.Button(toolbar_panel, label="Close", size=(80, 30))
        close_btn.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        toolbar_sizer.Add(close_btn, 0, wx.ALL, 5)
        
        toolbar_panel.SetSizer(toolbar_sizer)
        vbox.Add(toolbar_panel, 0, wx.EXPAND | wx.ALL, 5)
        
        # Create matplotlib figure inside the scrolled window
        self.figure = plt.figure(figsize=self.original_figsize, dpi=100, constrained_layout=True)
        self.canvas = FigureCanvas(self.scrolled_window, -1, self.figure)
        
        # Create sizer for scrolled window
        scroll_sizer = wx.BoxSizer(wx.VERTICAL)
        scroll_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 5)
        self.scrolled_window.SetSizer(scroll_sizer)
        
        vbox.Add(self.scrolled_window, 1, wx.EXPAND | wx.ALL, 5)
        
        # Status text (outside scrolled area)
        self.status_text = wx.StaticText(panel, label="Preparing plot...")
        vbox.Add(self.status_text, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        panel.SetSizer(vbox)
        
        # Bind keyboard shortcuts
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.canvas.SetFocus()  # Ensure canvas gets keyboard focus
        
        # Start plot generation after window is shown
        wx.CallLater(100, self.start_plot_generation)
    
    def on_zoom_in(self, event):
        """Zoom in by 25% (additive, not multiplicative)"""
        self.zoom_level += 0.25
        if self.zoom_level > 5.0:  # Max 500% zoom
            self.zoom_level = 5.0
        self.update_zoom()
    
    def on_zoom_out(self, event):
        """Zoom out by 25% (additive, not multiplicative)"""
        self.zoom_level -= 0.25
        if self.zoom_level < 0.25:  # Min 25% zoom
            self.zoom_level = 0.25
        self.update_zoom()
    
    def on_reset_zoom(self, event):
        """Reset zoom to 100%"""
        self.zoom_level = 1.0
        self.update_zoom()
    
    def on_autofit(self, event):
        """Auto-fit plot to window"""
        if self.plot_ready:
            # Get current scrolled window size
            width, height = self.scrolled_window.GetClientSize()
            
            # Calculate DPI based on window size and desired figure size
            dpi = 100  # Base DPI
            
            # Adjust figure size to fit window (with some padding)
            fig_width = width / dpi * 0.95  # 95% of window width
            fig_height = height / dpi * 0.9  # 90% of window height
            
            # Maintain aspect ratio
            orig_ratio = self.original_figsize[0] / self.original_figsize[1]
            new_ratio = fig_width / fig_height
            
            if new_ratio > orig_ratio:
                # Window is wider than figure - adjust width
                fig_width = fig_height * orig_ratio
            else:
                # Window is taller than figure - adjust height
                fig_height = fig_width / orig_ratio
            
            # Update original size for zoom reference
            self.original_figsize = (fig_width, fig_height)
            
            # Reset zoom level since we're auto-fitting
            self.zoom_level = 1.0
            
            # Update figure
            self.figure.set_size_inches(fig_width, fig_height)
            
            # Update constrained_layout parameters for new size
            self.figure.set_constrained_layout_pads(w_pad=0.04, h_pad=0.04, 
                                                   wspace=0.02, hspace=0.1)
            
            self.canvas.draw()
            self.zoom_label.SetLabel("100%")
            self.status_text.SetLabel("Plot auto-fitted to window")
            
            # Disable scrolling when auto-fitted
            self.scrolled_window.EnableScrolling(False, False)
    
    def update_zoom(self):
        """Update zoom level and redraw"""
        if self.plot_ready:
            # Update zoom label
            zoom_percent = int(self.zoom_level * 100)
            self.zoom_label.SetLabel(f"{zoom_percent}%")
            
            # Calculate new figure size based on original
            new_width = self.original_figsize[0] * self.zoom_level
            new_height = self.original_figsize[1] * self.zoom_level
            
            # Update figure size
            self.figure.set_size_inches(new_width, new_height)
            
            self.canvas.draw()
            
            # Update scrolled window virtual size based on canvas size
            canvas_size = self.canvas.GetSize()
            self.scrolled_window.SetVirtualSize(canvas_size)
            
            # Enable scrolling if plot is larger than window
            scroll_width, scroll_height = self.scrolled_window.GetClientSize()
            if canvas_size.width > scroll_width or canvas_size.height > scroll_height:
                self.scrolled_window.EnableScrolling(True, True)
                self.status_text.SetLabel(f"Zoom: {zoom_percent}% (Use scrollbars to navigate)")
            else:
                self.scrolled_window.EnableScrolling(False, False)
                self.status_text.SetLabel(f"Zoom: {zoom_percent}%")
            
            # Scroll to top-left when zooming
            self.scrolled_window.Scroll(0, 0)
    
    def on_key_down(self, event):
        """Handle keyboard shortcuts"""
        keycode = event.GetKeyCode()
        
        if keycode == wx.WXK_ADD or keycode == wx.WXK_NUMPAD_ADD or keycode == ord('+'):
            self.on_zoom_in(event)
        elif keycode == wx.WXK_SUBTRACT or keycode == wx.WXK_NUMPAD_SUBTRACT or keycode == ord('-'):
            self.on_zoom_out(event)
        elif keycode == wx.WXK_HOME or keycode == ord('0'):
            self.on_reset_zoom(event)
        elif keycode == ord('F') or keycode == wx.WXK_F11:
            self.on_autofit(event)
        elif keycode == wx.WXK_ESCAPE:
            self.Close()
        elif keycode == wx.WXK_PAGEUP:
            # Scroll up
            self.scrolled_window.ScrollLines(-10)
        elif keycode == wx.WXK_PAGEDOWN:
            # Scroll down
            self.scrolled_window.ScrollLines(10)
        elif keycode == wx.WXK_UP:
            # Scroll up a little
            self.scrolled_window.ScrollLines(-3)
        elif keycode == wx.WXK_DOWN:
            # Scroll down a little
            self.scrolled_window.ScrollLines(3)
        elif keycode == wx.WXK_LEFT:
            # Scroll left
            self.scrolled_window.ScrollLines(-3, horizontal=True)
        elif keycode == wx.WXK_RIGHT:
            # Scroll right
            self.scrolled_window.ScrollLines(3, horizontal=True)
        else:
            event.Skip()  # Pass other keys to default handler
    
    def on_save_plot(self, event):
        """Save plot to file"""
        if not self.plot_ready:
            wx.MessageBox("No plot to save. Please wait for plot generation.", 
                         "Warning", wx.OK | wx.ICON_WARNING, self)
            return
        
        with wx.FileDialog(self, "Save Plot As", wildcard="PNG files (*.png)|*.png|PDF files (*.pdf)|*.pdf|SVG files (*.svg)|*.svg",
                          style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            
            pathname = fileDialog.GetPath()
            file_format = pathname.split('.')[-1].lower() if '.' in pathname else 'png'
            
            try:
                # Save with high DPI for better quality
                self.figure.savefig(pathname, dpi=300, bbox_inches='tight', format=file_format)
                self.status_text.SetLabel(f"Plot saved to {pathname}")
                self.GetParent().SetStatusText(f"Plot saved: {pathname}")
                
                wx.MessageBox(f"Plot saved successfully to {pathname}", 
                             "Success", wx.OK | wx.ICON_INFORMATION, self)
                
            except Exception as e:
                wx.MessageBox(f"Error saving plot: {str(e)}", 
                             "Error", wx.OK | wx.ICON_ERROR, self)
    
    def start_plot_generation(self):
        """Start plot generation"""
        self.status_text.SetLabel("Extracting data... Please wait.")
        
        # Use a simpler approach - generate plot directly with wx.Yield to keep UI responsive
        wx.CallLater(50, self.generate_plot_direct)
    
    def generate_plot_direct(self):
        """Generate plot directly with periodic yields to keep UI responsive"""
        try:
            # Show we're working
            self.status_text.SetLabel("Extracting sensor data (0%)...")
            wx.Yield()  # Allow UI updates
            
            # Extract all sensor data with periodic updates
            all_sensor_data = []
            total_users = len(self.data)
            
            for i, user in enumerate(self.data):
                all_sensor_data.extend(user['sensor_data'])
                
                # Update status every 100 users
                if i % 100 == 0:
                    percent = int((i / total_users) * 100)
                    self.status_text.SetLabel(f"Extracting data ({percent}%)...")
                    wx.Yield()  # Allow UI updates
            
            if not all_sensor_data:
                self.status_text.SetLabel("No data available")
                return
            
            self.status_text.SetLabel("Creating DataFrame...")
            wx.Yield()
            
            df = pd.DataFrame(all_sensor_data)
            
            self.status_text.SetLabel("Generating plot...")
            wx.Yield()
            
            # Clear and create plot
            self.figure.clear()
            
            if self.plot_type == 'A':
                # Plot A: Density plot of outside temperature
                ax = self.figure.add_subplot(111)
                
                ax.hist(df['outside_temperature'], bins=150, density=True, 
                       edgecolor='black', alpha=0.7, color='blue')
                ax.set_xlabel('Outside Temperature (°F)', fontsize=12)
                ax.set_ylabel('Density', fontsize=12)
                ax.set_title(f'Density Plot of Outside Temperature\n({len(df):,} data points)', 
                           fontsize=14, fontweight='bold')
                ax.grid(True, alpha=0.3)
                
                stats_text = (f"Mean: {df['outside_temperature'].mean():.2f}°F\n"
                            f"Std Dev: {df['outside_temperature'].std():.2f}°F\n"
                            f"Range: {df['outside_temperature'].min():.2f} - "
                            f"{df['outside_temperature'].max():.2f}°F")
                ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                       verticalalignment='top', fontsize=10,
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            elif self.plot_type == 'B':
                # Plot B: Line graph of outside vs room temperature
                ax = self.figure.add_subplot(111)
                
                sample_size = min(500, len(df))
                x = range(sample_size)
                
                ax.plot(x, df['outside_temperature'].iloc[:sample_size], 
                       label='Outside Temperature', linewidth=2, color='red')
                ax.plot(x, df['room_temperature'].iloc[:sample_size], 
                       label='Room Temperature', linewidth=2, color='blue')
                ax.set_xlabel('Sample Index', fontsize=12)
                ax.set_ylabel('Temperature (°F)', fontsize=12)
                ax.set_title(f'Outside vs Room Temperature\n(First {sample_size:,} of {len(df):,} samples)', 
                           fontsize=14, fontweight='bold')
                ax.legend(fontsize=11, loc='best')
                ax.grid(True, alpha=0.3)
                
                diff = df['outside_temperature'].iloc[:sample_size] - df['room_temperature'].iloc[:sample_size]
                diff_text = (f"Average difference: {diff.mean():.2f}°F\n"
                           f"Max difference: {diff.max():.2f}°F")
                ax.text(0.02, 0.98, diff_text, transform=ax.transAxes,
                       verticalalignment='top', fontsize=10,
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            elif self.plot_type == 'C':
                # Plot C: Side-by-side density plots using constrained_layout
                self.figure.set_size_inches(12, 10)
                
                # Set constrained_layout to move plots DOWN (leave space at top for title)
                self.figure.set_constrained_layout({
                    'w_pad': 0.04,
                    'h_pad': 0.04,
                    'wspace': 0.02,
                    'hspace': 0.1,
                    'rect': (0, 0, 1, 0.92)  # Moves all plots down, leaves space at top
                })
                
                # Create 2x2 grid using add_subplot
                axes = []
                for i in range(4):
                    axes.append(self.figure.add_subplot(2, 2, i+1))
                
                data_list = [
                    df['outside_temperature'],
                    df['room_temperature'], 
                    df['outside_humidity'],
                    df['room_humidity']
                ]
                titles = ['Outside Temperature', 'Room Temperature', 
                         'Outside Humidity', 'Room Humidity']
                colors = ['blue', 'green', 'red', 'orange']
                units = ['°F', '°F', '%', '%']
                
                for idx, (data, title, color, unit) in enumerate(zip(data_list, titles, colors, units)):
                    ax = axes[idx]
                    
                    ax.hist(data, bins=200, density=True, alpha=0.7, 
                           color=color, edgecolor='black')
                    
                    ax.set_xlabel(f'{title} ({unit})', fontsize=9)
                    ax.set_ylabel('Density', fontsize=9)
                    ax.set_title(f'{title}\nn={len(data):,}', fontsize=10, fontweight='bold')
                    ax.grid(True, alpha=0.3)
                    
                    stats_text = (f"μ={data.mean():.2f}{unit}\n"
                                f"σ={data.std():.2f}{unit}\n"
                                f"Range: {data.min():.1f}-{data.max():.1f}{unit}")
                    ax.text(0.02, 0.90, stats_text, transform=ax.transAxes,
                           verticalalignment='top', fontsize=9,
                           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
                
                self.figure.suptitle(f'Density Distributions of All Measurements\nTotal: {len(df):,} data points', 
                                   fontsize=12, fontweight='bold', y=0.98)
            
            self.canvas.draw()
            self.status_text.SetLabel("Plot complete! Use +/- to zoom (25% steps), scrollbars to navigate.")
            self.plot_ready = True
            
            # Auto-fit initially
            wx.CallLater(500, self.on_autofit, None)
            
        except Exception as e:
            self.status_text.SetLabel(f"Error: {str(e)[:100]}")
            # Show error in status bar instead of message box
            self.GetParent().SetStatusText(f"Plot error: {str(e)[:100]}")

class MainWindow(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, title="IoT Data Generator", size=(1000, 700))
        
        self.data = None
        self.generation_in_progress = False
        self.current_plot_frame = None
        
        # Create menu bar
        menubar = wx.MenuBar()
        
        # File menu
        file_menu = wx.Menu()
        generate_item = file_menu.Append(wx.ID_ANY, 'Generate IoT Data', 'Generate artificial IoT data')
        save_json_item = file_menu.Append(wx.ID_ANY, 'Save as JSON', 'Save data as JSON file')
        save_csv_item = file_menu.Append(wx.ID_ANY, 'Save as CSV', 'Save data as CSV file')
        file_menu.AppendSeparator()
        exit_item = file_menu.Append(wx.ID_EXIT, 'Exit', 'Exit application')
        
        # Statistics menu
        stats_menu = wx.Menu()
        descriptive_item = stats_menu.Append(wx.ID_ANY, 'Descriptive Statistics', 'Show descriptive statistics')
        plot_a_item = stats_menu.Append(wx.ID_ANY, 'Plot A - Outside Temp Histogram', 'Show histogram of outside temperature')
        plot_b_item = stats_menu.Append(wx.ID_ANY, 'Plot B - Temp Comparison', 'Show line graph of outside vs room temperature')
        plot_c_item = stats_menu.Append(wx.ID_ANY, 'Plot C - All Distributions', 'Show histogram of all measurements')
        
        menubar.Append(file_menu, 'File')
        menubar.Append(stats_menu, 'Statistics')
        self.SetMenuBar(menubar)
        
        # Bind menu events
        self.Bind(wx.EVT_MENU, self.on_generate, generate_item)
        self.Bind(wx.EVT_MENU, self.on_save_json, save_json_item)
        self.Bind(wx.EVT_MENU, self.on_save_csv, save_csv_item)
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)
        self.Bind(wx.EVT_MENU, self.on_descriptive, descriptive_item)
        self.Bind(wx.EVT_MENU, self.on_plot_a, plot_a_item)
        self.Bind(wx.EVT_MENU, self.on_plot_b, plot_b_item)
        self.Bind(wx.EVT_MENU, self.on_plot_c, plot_c_item)
        
        # Create main panel
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(panel, label="IoT Data Generator", style=wx.ALIGN_CENTER)
        title_font = wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        vbox.Add(title, flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=20)
        
        # Instructions
        instructions = wx.StaticText(panel, label="Use the File menu to generate IoT data, then use Statistics menu to analyze it.")
        vbox.Add(instructions, flag=wx.ALIGN_CENTER | wx.BOTTOM, border=20)
        
        # Data info panel
        self.info_panel = wx.Panel(panel)
        info_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.data_info = wx.StaticText(self.info_panel, label="No data generated yet.")
        info_sizer.Add(self.data_info, flag=wx.ALL, border=10)
        
        self.progress_label = wx.StaticText(self.info_panel, label="")
        info_sizer.Add(self.progress_label, flag=wx.ALL, border=10)
        
        self.info_panel.SetSizer(info_sizer)
        vbox.Add(self.info_panel, flag=wx.EXPAND | wx.ALL, border=10)
        
        # Preview grid (initially hidden)
        self.grid = wx.grid.Grid(panel)
        self.grid.CreateGrid(0, 13)  # 13 columns for all data
        self.grid.Hide()
        
        # Set column labels
        columns = ['Firstname', 'Lastname', 'Age', 'Gender', 'Username', 'Address', 'Email',
                  'Date', 'Time', 'Outside Temp', 'Outside Hum', 'Room Temp', 'Room Hum']
        for i, col in enumerate(columns):
            self.grid.SetColLabelValue(i, col)
        
        vbox.Add(self.grid, proportion=1, flag=wx.EXPAND | wx.ALL, border=10)
        
        panel.SetSizer(vbox)
        
        # Create status bar
        self.CreateStatusBar()
        self.SetStatusText("Ready")
        
        self.Centre()
        self.Show(True)
    
    def on_generate(self, event):
        """Generate IoT data"""
        if self.generation_in_progress:
            wx.MessageBox("Data generation is already in progress!", "Warning", wx.OK | wx.ICON_WARNING)
            return
        
        # Close any open plot windows
        if self.current_plot_frame:
            self.current_plot_frame.Close()
            self.current_plot_frame = None
        
        # Confirm with user
        dlg = wx.MessageDialog(self, 
                              "This will generate 1000 user records with 1000 sensor records each.\nTotal: 1,000,000 sensor records.\nThis may take some time. Continue?",
                              "Confirm Generation", 
                              wx.YES_NO | wx.ICON_QUESTION)
        
        if dlg.ShowModal() == wx.ID_YES:
            # Start generation in separate thread
            self.generation_in_progress = True
            self.SetStatusText("Generating data... Please wait.")
            self.progress_label.SetLabel("Starting data generation...")
            self.data_info.SetLabel("Data generation in progress...")
            
            # Disable menu items during generation
            self.GetMenuBar().EnableTop(1, False)  # Disable Statistics menu
            
            thread = threading.Thread(target=self.generate_data_thread)
            thread.daemon = True
            thread.start()
        
        dlg.Destroy()
    
    def generate_data_thread(self):
        """Generate data in a separate thread"""
        try:
            wx.CallAfter(self.progress_label.SetLabel, "Generating 1000 user records...")
            # Generate user data
            self.data = IoTDataGenerator.generate_user_data(1000)
            wx.CallAfter(self.progress_label.SetLabel, "1000 user records created. Generating sensor data...")
            
            # Generate sensor data for each user
            total_users = len(self.data)
            for i, user in enumerate(self.data):
                user['sensor_data'] = IoTDataGenerator.generate_sensor_data_for_user()
                
                # Update progress every 10 users (more frequent updates)
                if i % 10 == 0:
                    progress = f"Generated sensor data for {i}/{total_users} users..."
                    wx.CallAfter(self.update_progress, progress)
                
                # Small delay to allow UI updates
                if i % 50 == 0:
                    time.sleep(0.01)
            
            # Update UI on main thread
            wx.CallAfter(self.data_generation_complete)
            
        except Exception as e:
            wx.CallAfter(self.data_generation_error, str(e))
    
    def update_progress(self, message):
        """Update progress label"""
        self.progress_label.SetLabel(message)
    
    def data_generation_complete(self):
        """Called when data generation is complete"""
        self.generation_in_progress = False
        self.SetStatusText("Data generation complete")
        self.progress_label.SetLabel("Data generation complete!")
        
        # Re-enable menu items
        self.GetMenuBar().EnableTop(1, True)  # Enable Statistics menu
        
        # Update data info
        total_sensors = sum(len(user['sensor_data']) for user in self.data)
        self.data_info.SetLabel(f"Generated {len(self.data):,} user records with {total_sensors:,} total sensor records")
        
        # Show preview of first few records
        self.show_data_preview()
        
        wx.MessageBox(f"Successfully generated {len(self.data):,} user records with {total_sensors:,} sensor records!", 
                     "Success", wx.OK | wx.ICON_INFORMATION)
    
    def data_generation_error(self, error_msg):
        """Called when data generation fails"""
        self.generation_in_progress = False
        self.SetStatusText("Data generation failed")
        self.progress_label.SetLabel("Data generation failed!")
        
        # Re-enable menu items
        self.GetMenuBar().EnableTop(1, True)  # Enable Statistics menu
        
        wx.MessageBox(f"Error generating data: {error_msg}", 
                     "Error", wx.OK | wx.ICON_ERROR)
    
    def show_data_preview(self):
        """Show a preview of the data in the grid"""
        if not self.data or len(self.data) == 0:
            return
        
        # Clear existing grid
        if self.grid.GetNumberRows() > 0:
            self.grid.DeleteRows(0, self.grid.GetNumberRows())
        
        # Add first few records for preview
        preview_count = min(10, len(self.data))
        row = 0
        
        for i in range(preview_count):
            user = self.data[i]
            if user['sensor_data']:
                sensor = user['sensor_data'][0]  # First sensor record
                
                self.grid.AppendRows(1)
                
                # User data
                self.grid.SetCellValue(row, 0, user['firstname'])
                self.grid.SetCellValue(row, 1, user['lastname'])
                self.grid.SetCellValue(row, 2, str(user['age']))
                self.grid.SetCellValue(row, 3, user['gender'])
                self.grid.SetCellValue(row, 4, user['username'])
                self.grid.SetCellValue(row, 5, user['address'][:50] + "..." if len(user['address']) > 50 else user['address'])
                self.grid.SetCellValue(row, 6, user['email'])
                
                # Sensor data
                self.grid.SetCellValue(row, 7, sensor['date'])
                self.grid.SetCellValue(row, 8, sensor['time'])
                self.grid.SetCellValue(row, 9, str(sensor['outside_temperature']))
                self.grid.SetCellValue(row, 10, str(sensor['outside_humidity']))
                self.grid.SetCellValue(row, 11, str(sensor['room_temperature']))
                self.grid.SetCellValue(row, 12, str(sensor['room_humidity']))
                
                row += 1
        
        # Auto-size columns
        self.grid.AutoSizeColumns()
        self.grid.Show()
        self.Layout()
    
    def on_save_json(self, event):
        """Save data as JSON file"""
        if not self.data:
            wx.MessageBox("No data to save. Please generate data first.", "Error", wx.OK | wx.ICON_ERROR)
            return
        
        with wx.FileDialog(self, "Save JSON file", wildcard="JSON files (*.json)|*.json",
                          style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            
            pathname = fileDialog.GetPath()
            
            try:
                # Convert data to JSON-serializable format
                json_data = []
                for user in self.data:
                    user_copy = user.copy()
                    json_data.append(user_copy)
                
                with open(pathname, 'w') as f:
                    json.dump(json_data, f, indent=2)
                
                wx.MessageBox(f"Data saved to {pathname}", "Success", wx.OK | wx.ICON_INFORMATION)
                self.SetStatusText(f"Data saved to {pathname}")
                
            except Exception as e:
                wx.MessageBox(f"Error saving file: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)
    
    def on_save_csv(self, event):
        """Save data as CSV file"""
        if not self.data:
            wx.MessageBox("No data to save. Please generate data first.", "Error", wx.OK | wx.ICON_ERROR)
            return
        
        with wx.FileDialog(self, "Save CSV file", wildcard="CSV files (*.csv)|*.csv",
                          style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            
            pathname = fileDialog.GetPath()
            
            try:
                # Prepare data for CSV
                csv_data = []
                headers = ['firstname', 'lastname', 'age', 'gender', 'username', 'address', 'email',
                          'date', 'time', 'outside_temperature', 'outside_humidity', 
                          'room_temperature', 'room_humidity']
                
                # Add headers
                csv_data.append(headers)
                
                # Add data (first 10000 records for performance)
                record_count = 0
                max_records = 10000
                
                for user in self.data:
                    for sensor in user['sensor_data']:
                        row = [
                            user['firstname'],
                            user['lastname'],
                            str(user['age']),
                            user['gender'],
                            user['username'],
                            user['address'],
                            user['email'],
                            sensor['date'],
                            sensor['time'],
                            str(sensor['outside_temperature']),
                            str(sensor['outside_humidity']),
                            str(sensor['room_temperature']),
                            str(sensor['room_humidity'])
                        ]
                        csv_data.append(row)
                        
                        record_count += 1
                        if record_count >= max_records:
                            break
                    
                    if record_count >= max_records:
                        break
                
                # Write to CSV
                with open(pathname, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerows(csv_data)
                
                wx.MessageBox(f"Data saved to {pathname}\nSaved {record_count} records.", 
                             "Success", wx.OK | wx.ICON_INFORMATION)
                self.SetStatusText(f"Data saved to {pathname}")
                
            except Exception as e:
                wx.MessageBox(f"Error saving file: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)
    
    def on_descriptive(self, event):
        """Show descriptive statistics dialog"""
        if not self.data:
            wx.MessageBox("No data available. Please generate data first.", "Error", wx.OK | wx.ICON_ERROR)
            return
        
        dlg = StatisticsDialog(self, self.data)
        dlg.ShowModal()
        dlg.Destroy()
    
    def on_plot_a(self, event):
        """Show Plot A"""
        if not self.data:
            wx.MessageBox("No data available. Please generate data first.", "Error", wx.OK | wx.ICON_ERROR)
            return
        
        # Close previous plot if open
        if self.current_plot_frame:
            self.current_plot_frame.Close()
        
        self.current_plot_frame = PlotFrame(self, "Plot A - Outside Temperature Density", self.data, 'A')
        self.current_plot_frame.Show()
    
    def on_plot_b(self, event):
        """Show Plot B"""
        if not self.data:
            wx.MessageBox("No data available. Please generate data first.", "Error", wx.OK | wx.ICON_ERROR)
            return
        
        # Close previous plot if open
        if self.current_plot_frame:
            self.current_plot_frame.Close()
        
        self.current_plot_frame = PlotFrame(self, "Plot B - Temperature Comparison", self.data, 'B')
        self.current_plot_frame.Show()
    
    def on_plot_c(self, event):
        """Show Plot C"""
        if not self.data:
            wx.MessageBox("No data available. Please generate data first.", "Error", wx.OK | wx.ICON_ERROR)
            return
        
        # Close previous plot if open
        if self.current_plot_frame:
            self.current_plot_frame.Close()
        
        self.current_plot_frame = PlotFrame(self, "Plot C - All Measurements Density", self.data, 'C')
        self.current_plot_frame.Show()
    
    def on_exit(self, event):
        """Exit application"""
        self.Close()

# Fix matplotlib cleanup issue with wxPython
import atexit
import matplotlib._pylab_helpers

@atexit.register
def cleanup_matplotlib():
    """Clean up matplotlib figures without causing wxPython errors"""
    for manager in list(matplotlib._pylab_helpers.Gcf._activeQue.values()):
        try:
            manager.destroy()
        except:
            pass

def main():
    app = wx.App(False)
    frame = MainWindow()
    app.MainLoop()

if __name__ == "__main__":
    main()