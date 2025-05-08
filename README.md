# GAGEWestUS_RTK
Contained within this README.md are instructions for use with screenshots of demo applications, as well as class attributes and methods for the rtkMachine class defined in the rtkMachine.py file.

## Instructions for use

### Unpack files
Unpack the rtkGDB.gdb and rtkMachine_v1.py files to a directory on your local machine.
DEMO: In my case, I have stored them on my desktop.  

!(/images/Screenshot 2025-05-08 182643.png)

### Open project with flight feature classes
These files are designed to work within an ArcGIS Project, in the map view. We can access the files directly in the python window, but you could also copy and paste some of this code to work in a jupyter notebook attached to the project.  
DEMO: In my case, I have opened a project named Blank_Testing with three feature classes to test: testing_point, testing_polyline, and testing_polygon.
### Connect rtkGDB.gdb
Add a geodatabase connection to connect rtkGDB.gdb to your active project. The script will run and store all outputs within this geodatabase, so it is important to have easy access to it.
### Load Code
Open the python window (under 'Analysis'), right click in the prompt line (where you type in code), and select 'Load Code'. Then, navigate to the rtkMachine_v1.py file, and select 'OK' to load the code from this file. Press enter to run the file (you may need to press enter twice), importing the necessary modules and creating the rtkMachine class.  
### Get paths
To run, this class has two required input parameters: the full path of the provided geodatabase, and the full path of the flight feature class file (NOTE: this is the path to the rtkGDB.gdb database, NOT the default project database). These parameters are path_to_gdb and path_to_flight_featureclass, respectively. Both should be created as r-strings (r"folder/pathfolder/pathfolder/rtkGDB.gdb") so that the backslashes are read in properly. You can access the paths of flight feature classes by right clicking them within your project geodatabase and selecting 'copy path', and you can access the path of the rtkGDB geodatabase by finding it in your connected Databases and doing the same.  
DEMO: In my case, the paths are

`gdb_path = r"C:\Users\cttillotson\Desktop\rtkGDB.gdb"`  
`fc_path_point = r"U:\Users\cttillotson\GIS420Advanced\Final_Project_Blank_testing\Blank_Testing.gdb\testing_point"`

### Run the rtkMachine
The rtkMachine can be run in two different ways: it can first be saved as an object to a variable name, such as xyz = rtkMachine(...), and then run using the .run method, which would look like this:

`xyz = rtkMachine(...)`   
`xyz.run()`

This allows you to access the .output_table object attribute, which is a pandas dataframe containing all the relevant information for the specified near points. If near points are drawn, all the information in the .output_table is also stored in that feature class. You could access the output table by running .output_table() on the rtkMachine object after it has run, like this:

`xyz.output_table()`

Alternatively, you can simply call the .run method without assigning the object a variable name, which will still create the feature class outputs if specified to do so. This would look like:

`rtkMachine(...).run()`

In my DEMO, I chose to run it as one command, like so:

`rtkMachine(path_to_gdb = gdb_path, path_to_flight_featureclass = fc_path_point).run()`  
### Access the outputs

Information about the nearest rtk points to the specified feature class will be stored, if drawn, in the feature 'Nearby_points{number of times the rtkMachine has been run}', and an output will be printed.

