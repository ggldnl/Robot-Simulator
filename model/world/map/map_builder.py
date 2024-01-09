from model.world.map.map import Map
from model.world.map.standard_map import StandardMap
from model.world.map.spatial_map import SpatialMap
from typing import Literal

default_params = {
    "obs_min_dist": 0.8,
    "obs_max_dist": 5.0,
    "obs_min_width": 0.2,
    "obs_max_width": 0.7,
    "obs_min_height": 0.4,
    "obs_max_height": 0.9,
    "obs_count": 40,
    "obs_min_lin_speed": -0.02,
    "obs_max_lin_speed": 0.02,
    "obs_min_ang_speed": -2.0,
    "obs_max_ang_speed": 2.0,
    "goal_min_dist": 3.0,
    "goal_max_dist": 5.0,
    "min_goal_clearance": 0.5,
    "map_type": "gridlike",
    "boundaries": True,
}


class MapBuilder:

    def __init__(self):

        self.params_dictionary = default_params

        """
        Map type specifies the data structures used to carry out the computations.
        Standard maps use simple lists, spatial maps use quad trees.
        TODO write a thread safe implementation for the rtree library.
        """
        self.map_type = 'standard'

        """
        Obstacles can be of type 'triangle', 'rectangle', 'pentagon', 'random'.
        """
        self.obstacles_type = 'rectangular'

    @classmethod
    def _check_range(cls, a, b, min_distance=None):
        """
        Checks if the range between a and b is valid and
        optionally if there is at least min_distance between
        the two extrema
        """
        if b >= a:
            raise ValueError(f'Invalid range [{a}:{b}]')

        if min_distance is not None:
            if b - a < min_distance:
                raise ValueError(f'Minimum distance between the extrema [{a}:{b}] is not respected')

    @classmethod
    def _check_non_negative(cls, val, strict=False):
        """
        Checks if the value is non-negative (strictly or not)
        """
        if strict:
            if val < 0:
                raise ValueError(f'Value that should be strictly non-negative is negative: {val}')
        else:
            if val <= 0:
                raise ValueError(f'Value that should be non-negative is negative: {val}')

    def set_obs_dist_range(self, obs_min_dist, obs_max_dist):
        self._check_range(obs_min_dist, obs_max_dist)
        self.params_dictionary['obs_min_dist'] = obs_min_dist
        self.params_dictionary['obs_max_dist'] = obs_max_dist
        return self

    def set_obs_min_width_range(self, obs_min_width, obs_max_width):
        self._check_range(obs_min_width, obs_max_width)
        self.params_dictionary['obs_min_width'] = obs_min_width
        self.params_dictionary['obs_max_width'] = obs_max_width
        return self

    def set_obs_min_height_range(self, obs_min_height, obs_max_height):
        self._check_range(obs_min_height, obs_max_height)
        self.params_dictionary['obs_min_height'] = obs_min_height
        self.params_dictionary['obs_max_height'] = obs_max_height
        return self

    def set_obs_count(self, obs_count):
        self._check_non_negative(obs_count, strict=False)
        self.params_dictionary['obs_count'] = obs_count
        return self

    def set_obs_linear_speed_range(self, obs_min_lin_speed, obs_max_lin_speed):
        self._check_range(obs_min_lin_speed, obs_max_lin_speed)
        self.params_dictionary['obs_min_lin_speed'] = obs_min_lin_speed
        self.params_dictionary['obs_max_lin_speed'] = obs_max_lin_speed
        return self

    def set_obs_angular_speed_range(self, obs_min_ang_speed, obs_max_ang_speed):
        self._check_range(obs_min_ang_speed, obs_max_ang_speed)
        self.params_dictionary['obs_min_ang_speed'] = obs_min_ang_speed
        self.params_dictionary['obs_max_ang_speed'] = obs_max_ang_speed
        return self

    def set_goal_dist_range(self, goal_min_dist, goal_max_dist):
        self._check_range(goal_min_dist, goal_max_dist)
        self.params_dictionary['goal_min_dist'] = goal_min_dist
        self.params_dictionary['goal_max_dist'] = goal_max_dist
        return self

    def set_type(self, map_type: Literal['standard', 'spatial']):
        self.map_type = map_type
        return self

    def set_obstacles_type(self, obstacles_type: Literal['triangle', 'rectangle', 'pentagon', 'random']):
        self.params_dictionary["obstacles_type"] = obstacles_type
        return self

    def enable_boundaries(self):
        self.params_dictionary['boundaries'] = True
        return self

    def disable_boundaries(self):
        self.params_dictionary['boundaries'] = False
        return self

    def build(self):

        if self.map_type == 'standard':
            map_arch = StandardMap
        else:
            map_arch = SpatialMap

        return map_arch(**self.params_dictionary)


if __name__ == '__main__':

    # Initialize the map
    map = (MapBuilder()
                .set_obs_moving_count(10)
                .set_obs_steady_count(20)
                .enable_boundaries()
                .build())

    # Initialize a robot
    from model.world.robot.robots.cobalt.cobalt import Cobalt
    robots = [Cobalt()]

    map.generate(robots)

    # Get the directory path of the current script and the map folder location
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    folder_dir = os.path.join(script_dir, 'maps')
    output_file = os.path.join(folder_dir, 'map_1_rectangle.json')

    map.save_as_json(output_file)
