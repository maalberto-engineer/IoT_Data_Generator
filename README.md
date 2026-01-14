IoT Data Generator Application

Overview
A comprehensive wxPython desktop application for generating, analyzing, and visualizing artificial IoT sensor data. The application 
creates realistic user and sensor records with temperature and humidity measurements, providing statistical analysis and interactive 
visualizations.

Features

 1. Data Generation
- Generate 1,000 user records with: First Name, Last Name, Age, Gender, Username, Address, Email
- Each user has 1,000 sensor records (1,000,000 total records)
- Sensor data includes: Date, Time, Outside Temperature, Outside Humidity, Room Temperature, Room Humidity
- Data spans from January 1, 2015 to present, sampled every 6 hours

 2. Data Export
- Save as JSON: Export all generated data in JSON format
- Save as CSV: Export data in CSV format (limited to first 10,000 records for performance)

 3. Statistical Analysis
- Descriptive Statistics: Comprehensive statistics including mean, standard deviation, min/max, quartiles
- Total counts, date ranges, and distribution metrics for all measurements

 4. Interactive Visualizations
- Plot A: Density histogram of outside temperature (all 1M data points)
- Plot B: Line graph comparing outside vs room temperature (first 500 samples)
- Plot C: 2×2 grid of density histograms for all four measurements:
  - Outside Temperature
  - Room Temperature  
  - Outside Humidity
  - Room Humidity

 5. Advanced Plot Features
- Zoom Controls: +25%/-25% zoom with keyboard shortcuts (+, -, 0, F)
- Auto-Fit: Automatically resize plot to fit window while maintaining aspect ratio
- Scrollable Windows: Automatic scrollbars when plots exceed window size
- Save Plots: Export plots as PNG, PDF, or SVG (300 DPI)
- Interactive Navigation: Arrow keys and Page Up/Down for scrolling zoomed plots

Requirements:

Python Packages
pip install wxpython faker pandas numpy matplotlib
