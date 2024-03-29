from model.controllers.sampling_based_algorithm import SamplingBased
from model.controllers.graph import Node
from model.controllers.graph import Edge

from model.geometry.point import Point

import numpy as np


class VNode(Node):
    def __init__(self, point, parent=None, cost=0, heuristic=0, valid=True):
        super().__init__(point, parent, cost, heuristic)
        self.valid = valid

    def __str__(self):
        return f'VNode ({self.point}, {"v" if self.valid else "n"})'

    def __repr__(self):
        return self.__str__()


class DynamicRRT(SamplingBased):
    """
    Dynamic RRT (RRT with basic replanning). This algorithm is a simple
    RRT extension; once it finds a path, it stores the path in a backup
    list (waypoints). If the path is disrupted by an obstacle, it needs
    to be recomputed. The DynamicRRT recomputes the path by taking
    nodes from the waypoints cache when recomputing the path with a
    given probability. It has two phases: planning (finding the first path)
    and replanning (update the path if it is invalid). The replanning
    generates a path very similar to the previous one
    """

    def __init__(self,
                 world_map,
                 start=Point(0, 0),
                 margin=0.2,
                 iterations_per_step=1,
                 max_iterations=5000,
                 goal_sample_rate=0.05,
                 step_length=0.2,
                 waypoint_sampling_rate=0.5
                 ):

        self.step_length = step_length
        self.waypoint_sample_rate = waypoint_sampling_rate

        # Boolean used to distinguish planning and replanning steps:
        # if False, goal has not been reached yet, map changes are disabled
        #       and the planning step is executed;
        # if True, goal has been reached, map changes are enabled and the path
        #       can be disrupted by them; the replanning step is executed to
        #       repair the path or to trim the invalidated nodes
        self.goal_reached = False

        # Boolean used to know if we need a path (planning/replanning)
        # or we need to look for updates
        self.need_for_path = True

        # We inherit the node and edge lists from the SamplingBased class

        self.waypoints = []  # Cached nodes

        self.path_nodes = []  # Equivalent to path, but containing nodes

        # Number of obstacles. This will be used to check if something has
        # changed and we need to trim the tree/update the path
        self.num_obstacles = len(world_map.obstacles)

        # Uniform with the interface (it expects the path to contain points)
        # self.path_wrapper = PathWrapper()

        super().__init__(
            world_map,
            start,
            margin=margin,
            iterations_per_step=iterations_per_step,
            max_iterations=max_iterations,
            dynamic=True,
            goal_sample_rate=goal_sample_rate
        )

    def pre_search(self):

        self.nodes = [VNode(self.start)]
        self.edges = []

        self.waypoints = []
        self.path_nodes = []
        self.need_for_path = True
        self.goal_reached = False
        self.num_obstacles = len(self.world_map.obstacles)

    def step_search(self):

        if self.need_for_path:

            self.world_map.disable()  # At every iteration, ensure map changes are not enabled

            self.planning()  # Will eventually set goal_found to True and need_for_path to False

        else:  # We have the path, we start checking for map updates

            self.world_map.enable()  # Ensure map changes are enabled

            # Changes occurred (different number of obstacles)
            if self.num_obstacles != len(self.world_map.obstacles):

                # Update the number of obstacles in the map
                self.num_obstacles = len(self.world_map.obstacles)

                # Invalidate the nodes by iterating through the edges and checking
                # where a collision happened
                self.invalidate_nodes()

                # Propagate the invalid flag from parent to child
                self.trim()

                # Extract waypoints from the invalidated portion of the nodes_path
                self.extract_waypoints()

                # Check if the path is invalid
                if self.is_path_invalid():
                    self.need_for_path = True

        # Update drawing list
        self.update_draw_list()

    def planning(self):

        node_rand = self.generate_random_node()
        node_near = self.nearest_neighbor(node_rand)
        node_new = self.new_state(node_near, node_rand)

        if node_new and not self.check_collision(node_near.point, node_new.point):
            self.nodes.append(node_new)
            self.edges.append(Edge(node_near, node_new))
            dist = node_new.point.distance(self.world_map.goal)

            if dist <= self.step_length:
                self.extract_path(node_new)

    def generate_random_node(self):
        """
        Return a ValidNode (VNode) instead of a Node. ValidNodes only have
        a boolean attribute that indicates whether they are valid or not.
        """

        p = np.random.random()

        if p < self.goal_sample_rate:
            return VNode(Point(self.world_map.goal.x, self.world_map.goal.y))
        elif self.goal_sample_rate <= p < self.waypoint_sample_rate and len(self.waypoints) > 0:
            waypoint_index = np.random.randint(0, len(self.waypoints))
            waypoint = self.waypoints[waypoint_index]
            self.waypoints.pop(waypoint_index)
            return waypoint
        else:
            x = np.random.uniform(self.world_map.map_boundaries[0], self.world_map.map_boundaries[2])
            y = np.random.uniform(self.world_map.map_boundaries[1], self.world_map.map_boundaries[3])
            return VNode(Point(x, y))

    def nearest_neighbor(self, n):
        """
        Returns the nearest node to the one passed as argument
        """

        return min(self.nodes, key=lambda nd: nd.point.distance(n.point))

    def new_state(self, node_start, node_end):
        """
        Given two nodes (each containing a point), returns a new node
        with a point that is distant from the start node at maximum
        step_length and that has the start node as parent
        """

        dist, theta = self.get_distance_and_angle(node_start, node_end)

        dist = min(self.step_length, dist)
        new_x = node_start.point.x + dist * np.cos(theta)
        new_y = node_start.point.y + dist * np.sin(theta)

        # new_y = round(new_y / self.search_step, 2) * self.search_step
        # new_x = round(new_x / self.search_step, 2) * self.search_step

        node_new = VNode(Point(new_x, new_y))
        node_new.parent = node_start

        return node_new

    def extract_path(self, node):
        """
        Sets the goal_reached boolean to True and returns a path,
        that is a list of Points. We start from the goal and we go
        back to the start point, then we reverse the path
        """

        self.goal_reached = True
        self.need_for_path = False

        self.path_nodes = [VNode(self.world_map.goal)]
        node_now = node

        # Iterate back from the goal to the start node
        while node_now.parent is not None:
            node_now = node_now.parent
            self.path_nodes.append(node_now)

        # Reverse the path
        self.path_nodes = self.path_nodes[::-1]

    def invalidate_nodes(self):
        """
        Check where there is an obstacle between two nodes and
        set them as invalid
        """

        for edge in self.edges:
            if self.check_collision(edge.parent_node.point, edge.child_node.point):
                edge.child_node.valid = False

    def invalidate_path(self):
        """
        Invalidate the Point path
        """

        # Find the first invalid node in the nodes_path
        first_invalid_node = None
        for node in self.path_nodes:
            if not node.valid:
                first_invalid_node = node
                break

        invalid_point_in_path_index = -1
        for i, point in enumerate(self.path):
            if point == first_invalid_node.point:
                invalid_point_in_path_index = i
                break

        self.path = self.path[:invalid_point_in_path_index]

    def is_path_invalid(self):
        """
        Check whether the path is invalid or not
        """

        for node in self.path_nodes:
            if not node.valid:
                return True
        return False

    def trim(self):
        """
        Propagate the invalid flag from parent to child
        """

        for node in self.nodes:

            # If the node has a parent and the parent is not valid
            if node.parent is not None and not node.parent.valid:

                # Set also the child as invalid
                node.valid = False

        self.nodes = [node for node in self.nodes if node.valid]
        self.edges = [Edge(node.parent, node) for node in self.nodes[1:len(self.nodes)]]

    def extract_waypoints(self):

        """
        self.waypoints = [VNode(self.world_map.goal)]
        node_now = node

        while node_now.parent is not None:
            node_now = node_now.parent
            self.waypoints.append(node_now)

        # Trim the path to the last valid point
        self.waypoints = self.waypoints[:self.waypoints.index(self.start_node)]

        self.waypoints = self.waypoints[::-1]
        """

        self.waypoints = [node for node in self.path_nodes if not node.valid]

    def post_search(self):

        # Create the real path
        if not self.need_for_path:
            self.path = [node.point for node in self.path_nodes]
