from model.geometry.point import Point
from model.geometry.segment import Segment
from model.geometry.shape import Shape

import numpy as np


class Polygon(Shape):

    def __init__(self, points):
        """
        :param points: a list of 2-dimensional vectors.
        """

        # Deep copy of the points array. While making the copy we can
        # find the centroid of the polygon

        self.points = []
        for point in points:
            if isinstance(point, Point):
                self.points.append(Point(point.x, point.y))  # copy it
            elif isinstance(point, tuple):
                self.points.append(Point(point[0], point[1]))
            elif isinstance(point, list):
                self.points.append(Point(point[0], point[1]))
            else:
                raise ValueError(f'Invalid object {point}')

        # Super will instantiate the pose object
        super().__init__()

        # Find the center and set pose x and y values
        self._find_center()

        # Find the enclosing radius
        self.radius = self._find_radius()

    def _find_radius(self):
        """
        Find the radius of a circle that fully encloses this polygon.
        Supposes that the center has already been found.
        """

        radius = 0
        for point in self.points:
            distance = np.sqrt((self.pose.x - point.x) ** 2 + (self.pose.y - point.y) ** 2)
            radius = max(radius, distance)

        return radius

    def _find_center(self):
        total_x = sum(point.x for point in self.points)
        total_y = sum(point.y for point in self.points)
        num_points = len(self.points)
        self.pose.x = total_x / num_points
        self.pose.y = total_y / num_points

    def get_bounds(self):
        return self.get_bounding_box()

    def to_point_array(self):
        return [[point.x, point.y] for point in self.points]

    def get_bounding_box(self):
        """
        Returns the bounding box of the polygon.
        """

        # Compute the bounding box (list of points)
        min_x = self.points[0].x
        max_x = self.points[0].x
        min_y = self.points[0].y
        max_y = self.points[0].y

        for point in self.points:
            min_x = min(min_x, point.x)
            max_x = max(max_x, point.x)
            min_y = min(min_y, point.y)
            max_y = max(max_y, point.y)

        return min_x, min_y, max_x, max_y

    def translate(self, offset_x, offset_y):

        for point in self.points:
            point.x += offset_x
            point.y += offset_y

        self.pose.x += offset_x
        self.pose.y += offset_y

    def rotate(self, angle):
        """
        Rotate around the center by the specified angle
        """

        # Apply rotation to each point
        for point in self.points:
            # Translate the point to the origin (center) of rotation
            translated_x = point.x - self.pose.x
            translated_y = point.y - self.pose.y

            # Perform the rotation
            new_x = translated_x * np.cos(angle) - translated_y * np.sin(angle)
            new_y = translated_x * np.sin(angle) + translated_y * np.cos(angle)

            # Translate the point back to its original position
            point.x = new_x + self.pose.x
            point.y = new_y + self.pose.y

    def transform(self, x, y, theta):
        self.translate(x, y)
        self.rotate(theta)

    def translate_to(self, x, y):
        offset_x = x - self.pose.x
        offset_y = y - self.pose.y
        self.translate(offset_x, offset_y)

    def rotate_to(self, target_angle):
        # Compute the angle difference
        angle_diff = target_angle - self.pose.theta
        self.rotate(angle_diff)

    def transform_to(self, x, y, theta):
        self.translate_to(x, y)
        self.rotate_to(theta)

    @classmethod
    def from_dict(cls, dictionary):

        # point_list = json.loads(dictionary['points'], object_hook=lambda d: Point(d['x'], d['y']))

        points = []
        for point_dictionary in dictionary['points']:
            points.append(Point.from_dict(point_dictionary))

        return Polygon(points)

    def to_dict(self):
        return {'points': [point.to_dict() for point in self.points], 'pose': self.pose.to_dict()}

    def get_edges(self):
        """
        Get the edges of a polygon
        """

        edges = []
        for i in range(len(self.points)):
            edge = Segment(self.points[i], self.points[(i + 1) % len(self.points)])
            edges.append(edge)
        return edges

    def rotate_around(self, x, y, angle):
        """
        Rotate the polygon around a specified point by the specified angle (in radians).
        """

        # Apply rotation to each point
        for point in self.points:

            # Translate the point to the origin (center) of rotation
            translated_x = point.x - x
            translated_y = point.y - y

            # Perform the rotation
            new_x = translated_x * np.cos(angle) - translated_y * np.sin(angle)
            new_y = translated_x * np.sin(angle) + translated_y * np.cos(angle)

            # Translate the point back to its original position
            point.x = new_x + x
            point.y = new_y + y

        # Update the center
        self._find_center()

    def project(self, axis):
        """
        Project the polygon onto an axis and return the min and max values
        """

        min_proj = float('inf')
        max_proj = float('-inf')
        for point in self.points:
            projection = point.x * axis.x + point.y * axis.y
            if projection < min_proj:
                min_proj = projection
            if projection > max_proj:
                max_proj = projection
        return min_proj, max_proj

    def copy(self):
        """
        Returns a deep copy of the polygon
        """

        # points = []
        # for point in self.points:
        #     points.append(Point(point.x, point.y))
        # return Polygon(points)

        return Polygon([point.copy() for point in self.points])

    def __eq__(self, other):

        if isinstance(other, Polygon):

            if len(self.points) != len(other.points):
                return False

            # Check equality for each point
            for p1, p2 in zip(self.points, other.points):
                if p1 != p2:
                    return False
            return True

        return False

    def __len__(self):
        """
        Return the number of vertex of the polygon
        """

        return len(self.points)

    def __str__(self):
        point_str = ', '.join(str(point) for point in self.points)
        return f"Polygon(points=[{point_str}])"

    def __repr__(self):
        return self.__str__()

    def __getitem__(self, item):

        if item < 0 or item > len(self.points) - 1:
            raise IndexError(f'Polygon point index out of range: {item}')
        return self.points[item]

    def __setitem__(self, key, value):

        if not isinstance(value, Point):
            raise ValueError(f'Invalid object {type(value)}; must be Point.')

        if key < 0 or key > len(self.points) - 1:
            raise IndexError(f'Polygon point index out of range: {key}')

        self.points[key] = value
        self.radius = self._find_radius()
        self._find_center()

    @classmethod
    def random_polygon(cls, num_sides, radius, noise=0.5, merge_near_points=0):
        """
        Returns a random polygon for which the circumscribed circle has
        center at the origin and the specified radius
        """

        if num_sides < 3:
            raise ValueError("Number of sides must be at least 3")

        angles = np.linspace(0, 2 * np.pi, num_sides, endpoint=False)

        # perturbed_points = []
        perturbed_points = {}

        for angle in angles:
            # Perturb the angle with Gaussian noise
            angle += np.random.normal(0, noise)
            angle = angle % (2 * np.pi)

            # Calculate the coordinates for the random point
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)

            # perturbed_points.append((x, y, angle))
            perturbed_points.update({angle: Point(x, y)})

        # Sort the array to have a convex polygon
        # sorted_perturbed_points = sorted(perturbed_points, key=lambda point: point[2])
        points = [perturbed_points[key] for key in sorted(perturbed_points.keys())]

        merged_points = []
        if merge_near_points > 0:
            merged_points.append(points[0])
            for i in range(1, len(points)):
                if points[i].distance(points[i - 1]) > merge_near_points:
                    merged_points.append(points[i])

            # If we have more than 2 points
            if len(merged_points) > 2:
                return cls(merged_points)
            else:
                return cls(points)

        else:
            return cls(points)

    @classmethod
    def point_buffer(cls, point, margin, num_points=4):
        """
        Returns the buffer of a point. The buffer of a point is by default a square around it
        with side specified by the margin parameter
        """

        if margin < 0:
            raise ValueError(f"Margin should be a positive number, {margin} was given instead.")

        if num_points < 0:
            raise ValueError(f"Number of point for the buffer should be a positive number, {num_points} was given instead.")

        points = []
        for i in range(num_points):
            points.append(
                Point(point.x + margin * np.cos(i * 2 * np.pi / num_points), point.y + margin * np.sin(i * 2 * np.pi / num_points))
            )

        return Polygon(points)

    @classmethod
    def segment_buffer(cls, segment, left_margin, right_margin):
        """
        Returns the buffer of a segment. The buffer of a segment is by default a rectangle around it
        with left and right sides specified by the left_margin and right_margin parameters respectively
        """

        if left_margin < 0:
            raise ValueError(f"Left margin should be a positive number, {left_margin} was given instead.")

        if right_margin < 0:
            raise ValueError(f"Right margin should be a positive number, {right_margin} was given instead.")

        A = segment.start
        B = segment.end

        AB = B - A

        # Compute the squared magnitude of AB
        mag_squared = AB.x ** 2 + AB.y ** 2

        # Avoid division by zero by checking if mag_squared is non-zero
        if mag_squared == 0:
            raise ValueError(f"Segment {segment} has zero length.")

        # Compute the unit vector u_AB
        u_AB = AB / np.sqrt(mag_squared)

        # Compute the normal vector n_AB
        n_AB = Point(-u_AB.y, u_AB.x)

        # Compute the vertices of the buffer
        C = A + left_margin * n_AB
        D = B + left_margin * n_AB
        E = B - right_margin * n_AB
        F = A - right_margin * n_AB

        # Create a polygon from the four corners of the rectangle
        buffer = Polygon([C, D, E, F])

        return buffer
