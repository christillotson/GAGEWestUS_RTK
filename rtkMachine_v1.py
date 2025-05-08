### imports
import numpy as np
import pandas as pd
from IPython.display import display


class rtkMachine:
    
    times_already_run = 0 # this will be created when the class is imported, so the class should only be imported once.

    # first, initialize the class
    def __init__(self,
                 path_to_gdb: str,
                 path_to_flight_featureclass: str,
                 num_close: int = 1,
                 stations_ok: list = [],
                 stations_unavailable: list = [],
                 draw_lines: bool = True,
                 delete_layers: bool = True,
                 delete_features: bool = True,
                 display_output_table: bool = True,
                 display_nearby_points: bool = True
        ) -> None: 

        self.num_close = num_close
        self.stations_ok = stations_ok
        self.stations_unavailable = stations_unavailable
        
        rtkMachine.times_already_run += 1
        
        self.path_to_gdb = path_to_gdb
        self.path_to_realtime = rf"{self.path_to_gdb}\realtime_points"
        self.path_to_flight_featureclass = path_to_flight_featureclass

        self.delete_layers = delete_layers
        self.delete_features = delete_features
        self.draw_lines = draw_lines
        self.display_output_table = display_output_table
        self.display_nearby_points = display_nearby_points
        
        self.working_layer_names = [] # every time a working layer is created, append the name string of the layer to this list. They should be removed at the end of .run using _remove_working_layers
        self.fc_Delete = [] # same thing but PATH to the feature class gdb. They should be removed at the end of .run (last step, after remove working layers), using _delete_working_layers_from_gdb

        self.aprx = arcpy.mp.ArcGISProject("CURRENT") # define current project
        self.mp = self.aprx.activeMap # get current map, will be most recently opened map
        self.map_string = self.mp.spatialReference.exportToString()

        return

    # method to first check to make sure inputs are OK
    def _check(self):
        
        # checking user input variables
        if type(self.path_to_gdb) is not str:
            raise Exception("path_to_gdb needs to be a string")
        if type(self.path_to_flight_featureclass) is not str:
            raise Exception("path_to_flight_featureclass needs to be a string")
        if type(self.num_close) is not int:
            raise Exception("num_close needs to be an integer")
        if type(self.stations_ok) is not list:
            raise Exception("stations_ok needs to be a list")
        for station in self.stations_ok:
            if type(station) is not str:
                raise Exception("stations_ok needs to be a list of OK stations names as strings")
        if type(self.stations_unavailable) is not list:
            raise Exception("stations_unavailable needs to be a list")
        for station in self.stations_unavailable:
            if type(station) is not str:
                raise Exception("stations_unavailable needs to be a list of Unavailable stations names as strings")
                
        if type(self.delete_layers) is not bool:
            raise Exception("delete_layers needs to be a boolean, True or False")
        if type(self.delete_layers) is not bool:
            raise Exception("delete_features needs to be a boolean, True or False")
        if type(self.draw_lines) is not bool:
            raise Exception("draw_lines needs to be a boolean, True or False")
            
        # checking the flight feature class itself
        if (arcpy.Describe(rf'{self.path_to_flight_featureclass}').shapeType == 'Polygon') or (arcpy.Describe(rf'{self.path_to_flight_featureclass}').shapeType == 'Polyline'):
            print('need to get centerpoint')
        elif arcpy.Describe(rf'{self.path_to_flight_featureclass}').shapeType == 'Point':
            print('will make a copy of point feature class to use as centerpoint')
        else:
            raise Exception("Feature class shapeType of flight plan needs to be a Polygon, Polyline, or Point. It should also be a single feature. Multipatch not supported. Multipoint support planned for future update.")
        if int(arcpy.GetCount_management(rf'{self.path_to_flight_featureclass}')[0]) != 1:
            raise Exception("Feature class of flight plan needs to have only one row (one feature). If multiple features are relevant, you could merge them as one multipart feature, or split into multiple feature classes. Note that Multipatches are not supported. Multipoint is not supported either, but planned to be implemented in a future update.")
            
    # method to make it work is run
    def run(self):

        self._check()
        
        self._modify_realtime_points()
        self._get_usable_realtime_points()
        self._get_center_point()
        self._generate_near_table()

        if self.draw_lines == True:
            self._create_FROM_points()
            self._create_NEAR_points()
            self._combine_NEAR_and_FROM_points()
            self._create_near_lines()

        self._get_output_stats()

        self._get_nearby_points()

        if self.delete_layers == True:
            self._remove_working_layers()
        if self.delete_features == True:
            self._delete_working_layers_from_gdb()
        return

    def _modify_realtime_points(self): 
        """
        string
        """
        # self.stations_ok
        #self.stations_unavailable

        # Create the path of the output
        # should be variable depending on where the gdb is and how many times this has been run within the session, default 0
        out_class_string = rf"{self.path_to_gdb}\realtime_points_workingcopy{rtkMachine.times_already_run}"

        # actually make the copied realtime points, to be modified
        arcpy.management.CopyFeatures(
            in_features=self.path_to_realtime,
            out_feature_class=out_class_string,
            config_keyword="",
            spatial_grid_1=None,
            spatial_grid_2=None,
            spatial_grid_3=None
        )
        
        # for each list (so this will basically be twice)
            # get indices
            # modify status values based on these indices

        counter = 0 # for keeping track of the index
        fc = out_class_string # feature class we will be iterating through and modifying
        field = ['pnum'] # field of the names of the stations
        list_of_names = [] # will get all the names of all the stations

        # this will get us all the names of stations in og data
        with arcpy.da.UpdateCursor(fc,field) as cursor:
            for row in cursor:
                counter += 1
                list_of_names.append(row[0])        

        # get the indexes of things we want to be changed, one way or another
        idxs_to_ok = []
        for item in self.stations_ok:
            idx_of_item = [idx for idx in range(len(list_of_names)) if list_of_names[idx] == item][0]
            idxs_to_ok.append(idx_of_item)

        idxs_to_unavailable = []
        for item in self.stations_unavailable:
            idx_of_item = [idx for idx in range(len(list_of_names)) if list_of_names[idx] == item][0]
            idxs_to_unavailable.append(idx_of_item)

        fc = out_class_string
        field = ['status']
        
        counter = 0
        with arcpy.da.UpdateCursor(fc,field) as cursor:
            for row in cursor:
                if counter in idxs_to_ok:
                    print(f'changing row index {counter} to OK')
                    row[0] = 'OK'
                    cursor.updateRow(row)
                counter += 1

        counter = 0
        with arcpy.da.UpdateCursor(fc,field) as cursor:
            for row in cursor:
                if counter in idxs_to_unavailable:
                    print(f'changing row index {counter} to Status Unavailable')
                    row[0] = 'Status Unavailable'
                    cursor.updateRow(row)
                counter += 1

        self.modified_realtime = out_class_string
        self.working_layer_names.append(f'realtime_points_workingcopy{rtkMachine.times_already_run}')
        self.fc_Delete.append(out_class_string)
        return 
        # hopefully this adds the new updated feature to the map, so that future selects work. If not, I need to figure out a way to select by attribute and make a copy entirely within the gdb
        # or somehow make a copy conditionally. IDK how to do this

    def _get_usable_realtime_points(self):

        self.usable_realtime = rf"{self.path_to_gdb}\realtime_points_status_ok{rtkMachine.times_already_run}"
        # create second copy of realtime points where the status is OK
        # takes in path of the class, should be modified before this step

        input_fc = self.modified_realtime
        output_fc = self.usable_realtime

        arcpy.Select_analysis(input_fc, output_fc, where_clause="status = 'OK'")
        
        self.working_layer_names.append(rf'realtime_points_status_ok{rtkMachine.times_already_run}')
        self.fc_Delete.append(self.usable_realtime)

        return

    def _get_center_point(self):

        self.centerpoint_path = rf"{self.path_to_gdb}\flight_centerpoint{rtkMachine.times_already_run}"

        if (arcpy.Describe(rf'{self.path_to_flight_featureclass}').shapeType == 'Polygon') or (arcpy.Describe(rf'{self.path_to_flight_featureclass}').shapeType == 'Polyline'):
            arcpy.management.FeatureToPoint(
                in_features=self.path_to_flight_featureclass,
                out_feature_class=self.centerpoint_path,
                point_location="CENTROID"
            )
        elif arcpy.Describe(rf'{self.path_to_flight_featureclass}').shapeType == 'Point':
            arcpy.management.CopyFeatures(
                in_features=self.path_to_flight_featureclass,
                out_feature_class=self.centerpoint_path,
                config_keyword="",
                spatial_grid_1=None,
                spatial_grid_2=None,
                spatial_grid_3=None
            )
        self.working_layer_names.append(rf"flight_centerpoint{rtkMachine.times_already_run}")
        self.fc_Delete.append(self.centerpoint_path)

        return

    def _generate_near_table(self):

        self.near_table_path = rf"{self.path_to_gdb}\flight_centerpoint_near_realtime_ok_table{rtkMachine.times_already_run}"
        arcpy.analysis.GenerateNearTable(
            in_features=rf"flight_centerpoint{rtkMachine.times_already_run}",
            near_features=self.usable_realtime,
            out_table=self.near_table_path,
            search_radius=None,
            location="LOCATION",
            angle="ANGLE",
            closest="ALL",
            closest_count=self.num_close,
            method="GEODESIC",
            distance_unit="Meters"
        )
        return

    def _create_FROM_points(self):

        self.FROM_points_path = rf"{self.path_to_gdb}\FROM_points{rtkMachine.times_already_run}"
        arcpy.management.XYTableToPoint(
            in_table=self.near_table_path,
            out_feature_class=self.FROM_points_path,
            x_field="FROM_X",
            y_field="FROM_Y",
            z_field=None,
            coordinate_system=''
        )
        self.working_layer_names.append(rf"FROM_points{rtkMachine.times_already_run}")
        self.fc_Delete.append(self.FROM_points_path)
        return

    def _create_NEAR_points(self):

        self.NEAR_points_path = rf"{self.path_to_gdb}\NEAR_points{rtkMachine.times_already_run}"
        arcpy.management.XYTableToPoint(
            in_table=self.near_table_path,
            out_feature_class=self.NEAR_points_path,
            x_field="NEAR_X",
            y_field="NEAR_Y",
            z_field=None,
            coordinate_system=''
        )
        self.working_layer_names.append(rf"NEAR_points{rtkMachine.times_already_run}")
        self.fc_Delete.append(self.NEAR_points_path)
        
        return

    def _combine_NEAR_and_FROM_points(self):
        self.combined_points_path = rf"{self.path_to_gdb}\combined_NEAR_FROM_points{rtkMachine.times_already_run}"
        arcpy.management.Merge(
            inputs=rf"{self.FROM_points_path};{self.NEAR_points_path}",
            output=self.combined_points_path,
            field_mappings=None,
            add_source="NO_SOURCE_INFO",
            field_match_mode="USE_FIRST_SCHEMA"
        )
        self.working_layer_names.append(rf"combined_NEAR_FROM_points{rtkMachine.times_already_run}")
        self.fc_Delete.append(self.combined_points_path)

    def _create_near_lines(self):

        self.near_lines_path = rf"{self.path_to_gdb}\Nearby_lines{rtkMachine.times_already_run}"
        arcpy.management.PointsToLine(
            Input_Features=self.combined_points_path,
            Output_Feature_Class=self.near_lines_path,
            Line_Field="NEAR_FID",
            Sort_Field=None,
            Close_Line="NO_CLOSE",
            Line_Construction_Method="TWO_POINT",
            Attribute_Source="NONE",
            Transfer_Fields=None
        )
        return

    def _get_nearby_points(self):
        # this references an output created in _get_output_stats (self.output_table) because it was easier to code, so it should be implemented after _get_output_stats is run

        self.Nearby_points_path = rf"{self.path_to_gdb}\Nearby_points{rtkMachine.times_already_run}"
        
        input_fc = self.usable_realtime
        output_fc = self.Nearby_points_path

        list_of_nears = self.output_table['OBJECTID'].to_list()

        where_string = f"OBJECTID = {int(list_of_nears[0])}"
        if len(list_of_nears) > 1:
            for i in range(len(list_of_nears) - 1):
                where_string += f" OR OBJECTID = {int(list_of_nears[i+1])}"

        arcpy.Select_analysis(input_fc, output_fc, where_clause=where_string)

        arcpy.management.AddField(in_table = self.Nearby_points_path, field_name = 'horizontal_error_est', field_type = 'FLOAT')
        arcpy.management.AddField(in_table = self.Nearby_points_path, field_name = 'vertical_error_est', field_type = 'FLOAT')
        arcpy.management.AddField(in_table = self.Nearby_points_path, field_name = 'distance_meters', field_type = 'FLOAT')

        fc = self.Nearby_points_path

        list_of_names = self.output_table['pnum'].to_list()
        list_of_horiz = self.output_table['horizontal_error_est'].to_list()
        list_of_vert = self.output_table['vertical_error_est'].to_list()
        list_of_dist = self.output_table['distance_meters'].to_list()

        horiz_dict = dict(zip(list_of_names, list_of_horiz))
        vert_dict = dict(zip(list_of_names, list_of_vert))
        dist_dict = dict(zip(list_of_names, list_of_dist))
        
        fields = ['pnum','horizontal_error_est']
        with arcpy.da.UpdateCursor(fc,fields) as cursor:
            for row in cursor:
                name = row[0]
                if name in list_of_names:
                    row[1] = horiz_dict[name]
                    cursor.updateRow(row)
                
        fields = ['pnum','vertical_error_est']
        with arcpy.da.UpdateCursor(fc,fields) as cursor:
            for row in cursor:
                name = row[0]
                if name in list_of_names:
                    row[1] = vert_dict[name]
                    cursor.updateRow(row)
                
        fields = ['pnum','distance_meters']
        with arcpy.da.UpdateCursor(fc,fields) as cursor:
            for row in cursor:
                name = row[0]
                if name in list_of_names:
                    row[1] = dist_dict[name]
                    cursor.updateRow(row)

        return

    def _get_output_stats(self):
        
        realtimefields = arcpy.ListFields(self.usable_realtime)
        realtime_field_names = []
        for field in realtimefields:
            realtime_field_names.append(field.baseName)
        realtime_field_names.remove('Shape')

        near_table_np = arcpy.da.TableToNumPyArray(in_table = self.near_table_path, field_names = ["OBJECTID", "NEAR_FID", "NEAR_RANK", "NEAR_DIST", "NEAR_ANGLE"])
        realtime_np = arcpy.da.FeatureClassToNumPyArray(in_table = self.usable_realtime, field_names = realtime_field_names)

        near_table_pd = pd.DataFrame(near_table_np)
        realtime_pd = pd.DataFrame(realtime_np)

        init_pd = pd.DataFrame()
        for i in range(len(near_table_pd)):
            
            nearpoint = near_table_pd.iloc[i]
            nearpoint_info = realtime_pd[realtime_pd['OBJECTID'] == nearpoint['NEAR_FID']]
            nearpoint_name = nearpoint_info['pnum'].iloc[0]
            nearpoint_error_horizontal = 8 + ((nearpoint['NEAR_DIST']*1.)/1000)
            nearpoint_error_vertical = 15 + ((nearpoint['NEAR_DIST']*1.)/1000)
            
            nearpoint_angle = nearpoint['NEAR_ANGLE']
            nearpoint_direction = 'Invalid placeholder string. If you see this, something went wrong with the direction calculation but this does not interrupt process'
        
            # these calculations are only valid if the method for the generate near table is geodesic. if it is modified to use planar, meanings of angles change.
            if 112.5 <= nearpoint_angle <= 157.5:
                nearpoint_direction = 'Southeast'
            if 67.5 < nearpoint_angle < 112.5:
                nearpoint_direction = 'East'
            if 22.5 <= nearpoint_angle <= 67.5:
                nearpoint_direction = 'Northeast'
            if -22.5 < nearpoint_angle < 22.5:
                nearpoint_direction = 'North'
            if -67.5 <= nearpoint_angle <= -22.5:
                nearpoint_direction = 'Northwest'
            if -112.5 < nearpoint_angle < -67.6:
                nearpoint_direction = 'West'
            if -157.5 <= nearpoint_angle <= -112.5:
                nearpoint_direction = 'Southwest'
            if (nearpoint_angle < -157.5) or (nearpoint_angle > 157.5):
                nearpoint_direction = 'South'
                
            print('\n')
            print(f"The nearest base station by a rank of {int(nearpoint['NEAR_RANK'])} is {nearpoint_name} at a distance of {round(nearpoint['NEAR_DIST'], 2)} meters to the {nearpoint_direction}.")
            print(f"Estimated Horizontal Error: {nearpoint_error_horizontal} milimeters. Estimated Vertical Error: {nearpoint_error_vertical} milimeters.")

            nearpoint_info.insert(loc = 20, column = 'horizontal_error_est', value = nearpoint_error_horizontal)
            nearpoint_info.insert(loc = 21, column = 'vertical_error_est', value = nearpoint_error_vertical)
            nearpoint_info.insert(loc = 22, column = 'distance_meters', value = nearpoint['NEAR_DIST'])
            
            init_pd = pd.concat([init_pd, nearpoint_info])
            
        print('\n')
        print('Information for all points accessible through .output_table object attribute.')
        self.output_table = init_pd

        return

    def _remove_working_layers(self):
        
        list_of_layernames_indexed = []
        for layer in self.mp.listLayers():
            name = layer.longName
            list_of_layernames_indexed.append(name)

        bad_layers = self.working_layer_names

        layer_idxs_to_remove = []
        for item in bad_layers:
            idx_of_item = [idx for idx in range(len(list_of_layernames_indexed)) if list_of_layernames_indexed[idx] == item][0]
            layer_idxs_to_remove.append(idx_of_item)

        idx = 0
        for layer in self.mp.listLayers():
            if idx in layer_idxs_to_remove:
                self.mp.removeLayer(layer)
            idx +=1
        arcpy.Delete_management(rf"flight_centerpoint_near_realtime_ok_table{rtkMachine.times_already_run}") 
        return

    def _delete_working_layers_from_gdb(self):

        for fc in self.fc_Delete:
            if arcpy.Exists(fc):
                arcpy.Delete_management(fc,"")
        arcpy.Delete_management(self.near_table_path)
        return