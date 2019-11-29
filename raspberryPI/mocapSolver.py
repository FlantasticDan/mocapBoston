import math
import os
import sys
import numpy as np
import mathutils
from itertools import combinations

RESOLUTION = (1632, 1232)

# Detections String ID Constants
COLOR_ID = ['red', 'yellow', 'green', 'cyan', 'blue', 'magenta', False]
PATTERN_ID = ['triangle', 'square', 'circle', 'slash', 'line', 'y', False]

def angleOfViewCalc(cam, aov, trackPos):

    '''Calculates the angle of view distortion on the projected
    track and adds that to the camera rotation.  Returns tuple.'''

    trackAOV = []

    # calculate the camera angle compensation based on track pixel positon
    trackAOV.append((float(trackPos[0]) - 0.5) * float(aov[0])) # x adjusts y
    trackAOV.append((float(trackPos[1]) - 0.5) * float(aov[1])) # z adjusts x

    # import camera rotational euler angles
    cameraEuler = mathutils.Euler((float(cam[0]), float(cam[1]), float(cam[2])))
    # rotate camera based on tracker-based compensations
    cameraEuler.rotate_axis('X', trackAOV[1])
    cameraEuler.rotate_axis('Y', -1 * trackAOV[0])

    return (cameraEuler.x, cameraEuler.y, cameraEuler.z)

def pointRotate(p1, p2, p0, theta):

    '''
    Returns a point rotated about an arbitrary axis in 3D.
    Positive angles are counter-clockwise looking down the axis toward the origin.
    The coordinate system is assumed to be right-hand.
    Arguments: 'axis p1', 'axis p2', 'p to be rotated', 'rotation (in radians)'
    Reference 'Rotate A Point About An Arbitrary Axis (3D)' - Paul Bourke
    '''

    # Modified from code written by Bruce Vaughan of BV Detailing & Design
    # http://paulbourke.net/geometry/rotate/PointRotate.py

    # Translate so axis is at origin
    p = []
    for point in range(0, 3):
        p.append(p0[point] - p1[point])

    # Initialize point q
    q = [0.0, 0.0, 0.0]
    N = []
    for point1 in range(0, 3):
        N.append(p2[point1] - p1[point1])

    Nm = math.sqrt(N[0]**2 + N[1]**2 + N[2]**2)

    # Rotation axis unit vector
    n = (N[0]/Nm, N[1]/Nm, N[2]/Nm)

    # Matrix common factors
    c = math.cos(theta)
    t = (1 - math.cos(theta))
    s = math.sin(theta)
    X = n[0]
    Y = n[1]
    Z = n[2]

    # Matrix 'M'
    d11 = t*X**2 + c
    d12 = t*X*Y - s*Z
    d13 = t*X*Z + s*Y
    d21 = t*X*Y + s*Z
    d22 = t*Y**2 + c
    d23 = t*Y*Z - s*X
    d31 = t*X*Z - s*Y
    d32 = t*Y*Z + s*X
    d33 = t*Z**2 + c

    #            |p.x|
    # Matrix 'M'*|p.y|
    #            |p.z|
    q[0] = d11*p[0] + d12*p[1] + d13*p[2]
    q[1] = d21*p[0] + d22*p[1] + d23*p[2]
    q[2] = d31*p[0] + d32*p[1] + d33*p[2]

    # Translate axis and rotated point back to original location
    answer = []
    for point2 in range(0, 3):
        answer.append(q[point2] + p1[point2])
    return answer

def pointsOnLine(camera, markerPosition):
    '''
    Calculates 2 points on the line drawn between the camera origin and the
    projected point on the track projection.  Returns as 2 numpy arrays.
    
    Args:
        camera: tuple in the form (posX, posY, posZ, rotX, rotY, rotZ, aovX, aovY)
        markerPosition: tuple in the form (x, y) where x and y are a percetage across the frame
    
    '''

    # extract camera variables
    originPoint = (camera[0], camera[1], camera[2])
    cameraRotation = (camera[3], camera[4], camera[5])
    cameraAOV = (camera[6], camera[7])

    # account for marker based angle modifers
    rotation = angleOfViewCalc(cameraRotation, cameraAOV, markerPosition)

    # rotate point projected from original camera position about origin
    cameraPoint = (0, 0, -1)
    xRotate = pointRotate((0, 0, 0), (5, 0, 0), cameraPoint, rotation[0])
    yRotate = pointRotate((0, 0, 0), (0, 5, 0), xRotate, rotation[1])
    zRotate = pointRotate((0, 0, 0), (0, 0, 5), yRotate, rotation[2])

    # translate offset point to align with camera position
    newPoint = []
    for r in range(0, 3):
        newPoint.append(zRotate[r] + float(originPoint[r]))

    return (np.array([originPoint[0], originPoint[1], originPoint[2]]),
            np.array([newPoint[0], newPoint[1], newPoint[2]]))

def closestDistanceBetweenLines(a0, a1, b0, b1):

    '''Given two lines defined by numpy.array pairs (a0,a1,b0,b1)
    Return the closest points on each segment and their distance'''

    # Modified from code written by Eric Vignola(Fnord):
    # https://stackoverflow.com/a/18994296

    # Calculate denomitator
    A = a1 - a0
    B = b1 - b0
    magA = np.linalg.norm(A)
    magB = np.linalg.norm(B)

    _A = A / magA
    _B = B / magB

    cross = np.cross(_A, _B)
    denom = np.linalg.norm(cross)**2

    # If lines are parallel (denom=0) test if lines overlap.
    # If they don't overlap then there is a closest point solution.
    # If they do overlap, there are infinite closest positions, but there is a closest distance
    if not denom:
        d0 = np.dot(_A, (b0-a0))

        # Segments overlap, return distance between parallel segments
        return None, None, np.linalg.norm(((d0*_A)+a0)-b0)

    # Lines criss-cross: Calculate the projected closest points
    t = (b0 - a0)
    detA = np.linalg.det([t, _B, cross])
    detB = np.linalg.det([t, _A, cross])

    t0 = detA/denom
    t1 = detB/denom

    pA = a0 + (_A * t0) # Projected closest point on segment A
    pB = b0 + (_B * t1) # Projected closest point on segment B

    return pA, pB, np.linalg.norm(pA-pB)

def lineCross(markerPositionA, markerPositionB, cameraA, cameraB):
    '''
    Finds the closest point of 2 projected lines.
    
    Args:
        markerPositionA: tuple in the form (x, y) where x and y are a percetage across the frame of camera A
        markerPositionB: tuple in the form (x, y) where x and y are a percetage across the frame of camera B
        cameraA: tuple in the form (posX, posY, posZ, rotX, rotY, rotZ, aovX, aovY)
        cameraB: tuple in the form (posX, posY, posZ, rotX, rotY, rotZ, aovX, aovY)
    
    Returns:
        3D Point of Interection & Distance Between the Two Lines
        (x, y, z, distance)

    '''

    # define lines
    lineA = pointsOnLine(cameraA, markerPositionA)
    lineB = pointsOnLine(cameraB, markerPositionB)

    # calculate intersect
    intersect = closestDistanceBetweenLines(lineA[0].astype('float64'),
                                            lineA[1].astype('float64'),
                                            lineB[0].astype('float64'),
                                            lineB[1].astype('float64'))

    # define intersecting points and line
    pointA = intersect[0].tolist()
    pointB = intersect[1].tolist()
    lineDistance = intersect[2]

    # calculate midpoint
    midpoint = []
    for q in range(0, 3):
        midpoint.append((pointA[q] + pointB[q]) / 2)
    midpoint.append(lineDistance)
    return midpoint # (x, y, z, distance)

def solveFrame(*persp):
    """
    Solve all markers for the given frame.
    
    Args:
        (marker dictionary, camera)

    Returns:
        List in the form of ("{color} {pattern}", (x, y, z), distance)
    """

    # Check for Enough Camera Angles
    if len(persp) < 2:
        raise Exception
    
    # Create List to Recieve Solved Points
    solved = []

    # Loop Though Each Possible Marker
    for color in COLOR_ID:
        for pattern in PATTERN_ID:
            markers = []

            # For each marker check each perspective for detection
            for angle in persp:
                if angle[0][color][pattern] is not None:
                    markers.append((angle[0][color][pattern][0], angle[1]))
            
            # If marker was detected in at least 2 angles, triangulate the 3D Point
            if len(markers) > 1:
                sets = combinations(markers, 2)
                points = []

                # Triangulate the Point from Each Possible Pair of Detected Perspectives
                for pair in sets:
                    markerA = pair[0][0]
                    a = (markerA[0] / RESOLUTION[0], markerA[1] / RESOLUTION[1])
                    cameraA = pair[0][1]
                    markerB = pair[1][0]
                    b = (markerB[0] / RESOLUTION[0], markerB[1] / RESOLUTION[1])
                    cameraB = pair[1][1]

                    points.append(lineCross(a, b, cameraA, cameraB))
                
                # Average Triangulated Points together if necessary
                if len(points) > 1:
                    x = 0
                    y = 0
                    z = 0
                    d = 0
                    for coord in points:
                        x += coord[0]
                        y += coord[1]
                        z += coord[2]
                        d += coord[3]
                    x = x / len(points)
                    y = y / len(points)
                    z = z / len(points)
                    d = d / len(points)

                    solved.append(("{} {}".format(color, pattern), (x, y, z), d))
                else:
                    solved.append(("{} {}".format(color, pattern), (points[0], points[1], points[2]), points[3]))
    
    return solved