from model.controllers.search_based_algorithm import SearchBased

from model.geometry.segment import Segment
from model.geometry.point import Point
from enum import Enum

"""
May the code in this file rest eternally unseen, forgotten in the annals of time as a testament to its own ugliness.
"""


class State(Enum):
    NEW = 0
    CLOSED = 1
    OPEN = 2


class Step(Enum):
    PLANNING = 0
    REPLANNING = 1
    UPDATING_COST = 2
    DONE = 3


class Node:

    def __init__(self, point, state=State.NEW, k=0.0, h=float('inf'), parent=None, occupied=False):
        self.point = point
        self.state = state

        # The key value is used to prioritize states for exploration
        # and determines their importance in the search process.
        self.k = k
        self.h = h
        self.parent = parent
        self.occupied = occupied

    def __eq__(self, other):
        if not isinstance(other, Node):
            return False
        return self.point == other.point  # and self.state == other.state

    def __hash__(self):
        return hash(self.point)

    def __str__(self):
        return f'N[{self.point.x}, {self.point.y}]'

    def __repr__(self):
        return self.__str__()

    def distance(self, other):
        return self.point.distance(other.point)


class DynamicAStar(SearchBased):
    """
    The algorithm works by iteratively selecting a node from the open set and evaluating it.
    D* begins by searching backwards from the goal node towards the start node. Each expanded
    node has a back pointer which refers to the next node leading to the target, and each node
    knows the exact cost to the target.
    """

    def __init__(self,
                 world_map,
                 start=Point(0, 0),
                 margin=0.2,
                 iterations_per_step=4,
                 max_iterations=5000,
                 discretization_step=0.2,
                 ):

        # My other implementations dynamically create nodes from a continuous map
        # for search based algorithms. For this algorithm I'll try to keep things
        # simple as the overally complexity is much higher than other algorithms
        self.grid = None
        self.start_node = None
        self.goal_node = None

        # Enum used to know if we need a path (planning), if we had a path and
        # we need to modify it (replanning) or if we need to update the costs
        self.algorithm_step = None

        self.replanning_current_node = None  # This will come in handy later ;)
        self.cost_updated = False  # This too ;)

        # Whenever we have a path and self.has_path() returns True, the robot
        # will start moving towards the goal. We want instead the robot to move
        # only when the iterations are expired so we can add obstacles to the map.
        # For this reason we will store a temporary path and transfer all the points
        # from the temp path to the real one only once the iterations are expired.
        self.temp_path = None

        # Number of obstacles. This will be used to check if something has
        # changed and we need to trim the tree/update the path
        self.num_obstacles = len(world_map.obstacles)

        # We already have open and visited sets (open_set, closed_set respectively)
        # in the interface. The open set contains nodes that are candidates for
        # expansion; these are nodes that have been discovered but not yet fully
        # explored. The visited set (sometimes referred to as the closed set in
        # other algorithms like A*) contains nodes that have been fully explored.

        super().__init__(
            world_map,
            start,
            margin=margin,
            iterations_per_step=iterations_per_step,
            max_iterations=max_iterations,
            dynamic=True,
            discretization_step=discretization_step
        )

    def initialize_grid(self):
        """
        Initialize the cell grid
        """

        min_x, min_y, max_x, max_y = self.world_map.map_boundaries
        step = self.discretization_step

        x_values = [round(min_x + step * i, 2) for i in range(int((max_x - min_x) / step) + 1)]
        y_values = [round(min_y + step * i, 2) for i in range(int((max_y - min_y) / step) + 1)]

        self.grid = {}
        for y in y_values:
            for x in x_values:
                self.grid[(x, y)] = Node(Point(x, y))

    def can_run(self):
        # Continue processing nodes until there are no more iterations left and
        # the start node is marked as closed
        return self.current_iteration < self.max_iterations

    def get_from_grid(self, point):
        return self.grid[(point.x, point.y)]

    def pre_search(self):

        # Initialize the sets
        self.open_set = set()
        self.closed_set = set()

        self.algorithm_step = Step.PLANNING

        self.replanning_current_node = None
        self.cost_updated = False

        # Number of obstacles. This will be used to check if something has
        # changed and we need to trim the tree/update the path
        self.num_obstacles = len(self.world_map.obstacles)

        self.temp_path = []

        self.initialize_grid()
        self.start_node = self.get_from_grid(self.start)

        # Approximate the goal node to the nearest cell
        goal = self.world_map.goal
        nearest_x = round(round(goal.x / self.discretization_step) * self.discretization_step, 2)
        nearest_y = round(round(goal.y / self.discretization_step) * self.discretization_step, 2)
        goal_nearest_point = Point(nearest_x, nearest_y)

        # Set goal node's h value to 0
        self.goal_node = self.get_from_grid(goal_nearest_point)
        self.goal_node.h = 0

        # Insert goal node into open set
        self.insert(self.goal_node, 0)

    def delete(self, node):
        """
        Remove a node from the open set
        """

        if node.state == State.OPEN:
            node.state = State.CLOSED
        self.open_set.remove(node)

    def insert(self, node, new_h):
        """
        Insert the node into the open set
        """

        if node.state == State.NEW:
            node.k = new_h
        elif node.state == State.OPEN:
            node.k = min(node.k, new_h)
        elif node.state == State.CLOSED:
            node.k = min(node.h, new_h)

        node.h = new_h
        node.state = State.OPEN
        self.open_set.add(node)

    def get_k_min(self):
        """
        Computes the minimum value of the cost estimate (k)
        among all nodes in the open set
        """

        if not self.open_set:
            return -1
        return min([x.k for x in self.open_set])

    def min_state(self):
        """
        Select the node from the open set with the minimum k value
        """

        if not self.open_set:
            return None
        return min(self.open_set, key=lambda x: x.k)

    def cost(self, node_1, node_2):
        if self.check_collision(node_1.point, node_2.point):
            return float("inf")
        return node_1.distance(node_2)

    def post_search(self):
        self.path = []
        for point in self.temp_path:
            self.path.append(point)

    def extract_path(self):

        # Reset the path
        self.temp_path = []

        current_point = self.start_node
        while current_point is not None:
            self.temp_path.append(current_point.point)
            current_point = current_point.parent

    def get_neighboring_nodes(self, node):
        """
        Returns a list of neighboring nodes of a given state node
        on the grid
        """

        neighbors = set()
        for i in range(-1, 2):
            for j in range(-1, 2):
                if not (i == 0 and j == 0):
                    x = round(node.point.x + i * self.discretization_step, 2)
                    y = round(node.point.y + j * self.discretization_step, 2)
                    if (self.world_map.map_boundaries[0] <= x < self.world_map.map_boundaries[2] and
                            self.world_map.map_boundaries[1] <= y < self.world_map.map_boundaries[3]):
                        neighbor_node = self.grid[(x, y)]
                        if not self.check_collision(node.point, neighbor_node.point):
                            neighbors.add(neighbor_node)
        return neighbors

    def is_temp_path_invalid(self):
        for i in range(1, len(self.temp_path)):
            if self.check_collision(self.temp_path[i - 1], self.temp_path[i]):
                return True
        return False

    def step_search(self):
        """
        I'm loosing my sanity
        """

        if self.algorithm_step == Step.PLANNING:

            # At every iteration, ensure map changes are not enabled
            self.world_map.disable()

            self.planning()

            if self.start_node.state == State.CLOSED:

                self.extract_path()

                # We don't need to further search for the path
                self.algorithm_step = Step.DONE

        # We have the path, we start checking for wmap updates
        elif self.algorithm_step == Step.DONE:

            self.world_map.enable()  # Ensure map changes are enabled

            # Changes occurred (different number of obstacles)
            if self.num_obstacles != len(self.world_map.obstacles):

                # Update the number of obstacles in the map
                self.num_obstacles = len(self.world_map.obstacles)

                # Check if the path is invalid
                if self.is_temp_path_invalid():
                    self.algorithm_step = Step.REPLANNING
                    self.closed_set = set()
                    self.temp_path = []

        elif self.algorithm_step == Step.REPLANNING:
            """
            s = self.start_node
            while s != self.goal_node:
                if self.check_collision(s.point, s.parent.point):
                    self.modify(s)
                    continue
                s = s.parent
    
            self.extract_path()
            """

            self.world_map.disable()

            if self.replanning_current_node is None:
                self.replanning_current_node = self.start_node

            elif self.replanning_current_node != self.goal_node:
                if self.check_collision(self.replanning_current_node.point, self.replanning_current_node.parent.point):
                    self.modify_cost(self.replanning_current_node)
                    self.algorithm_step = Step.UPDATING_COST
                else:
                    self.replanning_current_node = self.replanning_current_node.parent

            elif self.replanning_current_node == self.goal_node:
                self.extract_path()
                self.replanning_current_node = None
                self.algorithm_step = Step.DONE

        elif self.algorithm_step == Step.UPDATING_COST:

            k_min = self.planning()
            if k_min >= self.replanning_current_node.h:
                self.algorithm_step = Step.REPLANNING

        # Update drawing list
        self.update_draw_list()

    def planning(self):

        # Step 1: Select a node from the open set with the minimum k value
        s = self.min_state()

        # Add the selected node to the visited set
        self.closed_set.add(s)

        # If there are no states in the open set or if the selected state is None, return -1
        if s is None:
            return -1

        # Record the minimum k value of this iteration (min path cost)
        k_old = self.get_k_min()

        # Step 2: Mark the selected node as visited (state = CLOSED)
        self.delete(s)

        # Step 3: Update the costs (h) of neighboring nodes based on the current node
        if k_old < s.h:
            for neighbor in self.get_neighboring_nodes(s):
                if (neighbor.h <= k_old and
                        s.h > neighbor.h + self.cost(neighbor, s)):
                    s.parent = neighbor
                    s.h = neighbor.h + self.cost(neighbor, s)

        # Step 4: Update nodes if the minimum path cost (k) changes
        if k_old == s.h:
            for neighbor in self.get_neighboring_nodes(s):
                if (neighbor.state == State.NEW or
                        (neighbor.parent == s and neighbor.h != s.h + self.cost(s, neighbor)) or
                        (neighbor.parent != s and neighbor.h > s.h + self.cost(s, neighbor))):
                    # Update h value and insert the node into the open set
                    neighbor.parent = s
                    self.insert(neighbor, s.h + self.cost(s, neighbor))

        else:
            for neighbor in self.get_neighboring_nodes(s):
                if (neighbor.state == State.NEW or
                        (neighbor.parent == s and neighbor.h != s.h + self.cost(s, neighbor))):

                    # Update h value and insert the state into the open set
                    neighbor.parent = s
                    self.insert(neighbor, s.h + self.cost(s, neighbor))
                else:
                    if (neighbor.parent != s and
                            neighbor.h > s.h + self.cost(s, neighbor)):

                        # Insert s into the open set again for further exploration
                        self.insert(s, s.h)

                    elif (neighbor.parent != s and
                          s.h > neighbor.h + self.cost(neighbor, s) and
                          neighbor.state == State.CLOSED and
                          neighbor.k > k_old):

                        # Insert neighbor into the open set again for further exploration
                        self.insert(neighbor, neighbor.h)

        return self.get_k_min()

    def replanning(self):

        s = self.start_node
        while s != self.goal_node:
            if self.check_collision(s.point, s.parent.point):
                self.modify(s)
                continue
            s = s.parent

        self.extract_path()

    def modify(self, node):
        """
        Start processing from the node
        """

        self.modify_cost(node)

        while True:
            k_min = self.planning()
            if k_min >= node.h:
                break

    def modify_cost(self, s):
        """
        If the node is in the closed set, put it into open set.
        Since cost may be changed between s - s.parent, calc cost(s, s.p) again
        """

        if s.state == State.CLOSED:
            self.insert(s, s.parent.h + self.cost(s, s.parent))

    def update_draw_list(self):
        # Overload the method to empty the draw_list first, getting rid of old segments.
        self.draw_list = []
        for node in self.open_set:
            self.draw_list.append(self.get_view(node.point))

        # Add the temp path if it has been found
        if len(self.temp_path) > 1:
            # self.draw_list.append(self.temp_path[0])
            for i in range(1, len(self.temp_path)):
                # self.draw_list.append(self.temp_path[i])
                self.draw_list.append(Segment(self.temp_path[i-1], self.temp_path[i]))
