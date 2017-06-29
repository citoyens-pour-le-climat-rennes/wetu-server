// found this at https://github.com/STRd6/MMatrix.js

/**
* MMatrix.js v1.2.0
* 
* Copyright (c) 2010 STRd6
*
* Permission is hereby granted, free of charge, to any person obtaining a copy
* of this software and associated documentation files (the "Software"), to deal
* in the Software without restriction, including without limitation the rights
* to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
* copies of the Software, and to permit persons to whom the Software is
* furnished to do so, subject to the following conditions:
*
* The above copyright notice and this permission notice shall be included in
* all copies or substantial portions of the Software.
*
* THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
* IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
* FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
* AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
* LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
* OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
* THE SOFTWARE.
*
* Loosely based on flash:
* http://www.adobe.com/livedocs/flash/9.0/ActionScriptLangRefV3/flash/geom/MMatrix.html
*/
(function() {
  /**
   * Create a new MPoint with given x and y coordinates. If no arguments are given
   * defaults to (0, 0).
   * @name MPoint
   * @param {Number} [x]
   * @param {Number} [y]
   * @constructor
   */
  function MPoint(x, y) {
    return {
      /**
       * The x coordinate of this MPoint.
       * @name x
       * @fieldOf MPoint#
       */
      x: x || 0,
      /**
       * The y coordinate of this MPoint.
       * @name y
       * @fieldOf MPoint#
       */
      y: y || 0,
      /**
       * Check whether two MPoints are equal. The x and y values must be exactly
       * equal for this method to return true.
       * @name equal
       * @methodOf MPoint#
       *
       * @param {MPoint} other The MPoint to check for equality.
       * @returns true if this MPoint is equal to the other MPoint, false
       * otherwise.
       * @type Boolean
       */
      equal: function(other) {
        return this.x === other.x && this.y === other.y;
      },
      /**
       * Adds a MPoint to this one and returns the new MPoint.
       * @name add
       * @methodOf MPoint#
       *
       * @param {MPoint} other The MPoint to add this MPoint to.
       * @returns A new MPoint, the sum of both.
       * @type MPoint
       */
      add: function(other) {
        return MPoint(this.x + other.x, this.y + other.y);
      },
      /**
       * Subtracts a MPoint from this one and returns the new MPoint.
       * @name subtract
       * @methodOf MPoint#
       *
       * @param {MPoint} other The MPoint to subtract from this MPoint.
       * @returns A new MPoint, the difference of both.
       * @type MPoint
       */
      subtract: function(other) {
        return MPoint(this.x - other.x, this.y - other.y);
      },
      /**
       * Multiplies this MPoint by a scalar value and returns the new MPoint.
       * @name scale
       * @methodOf MPoint#
       *
       * @param {MPoint} scalar The value to scale this MPoint by.
       * @returns A new MPoint with x and y multiplied by the scalar value.
       * @type MPoint
       */
      scale: function(scalar) {
        return MPoint(this.x * scalar, this.y * scalar);
      },
      /**
       * Returns the distance of this MPoint from the origin. If this MPoint is
       * thought of as a vector this distance is its magnitude.
       * @name magnitude
       * @methodOf MPoint#
       *
       * @returns The distance of this MPoint from the origin.
       * @type Number
       */
      magnitude: function() {
        return MPoint.distance(MPoint(0, 0), this);
      }
    };
  }

  /**
   * @param {MPoint} p1
   * @param {MPoint} p2
   * @returns The Euclidean distance between two MPoints.
   */
  MPoint.distance = function(p1, p2) {
    return Math.sqrt(Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2));
  };

  /**
   * If you have two dudes, one standing at MPoint p1, and the other
   * standing at MPoint p2, then this method will return the direction
   * that the dude standing at p1 will need to face to look at p2.
   * @param {MPoint} p1 The starting MPoint.
   * @param {MPoint} p2 The ending MPoint.
   * @returns The direction from p1 to p2 in radians.
   */
  MPoint.direction = function(p1, p2) {
    return Math.atan2(
      p2.y - p1.y,
      p2.x - p1.x
    );
  };

  /**
   * <pre>
   *  _        _
   * | a  c tx  |
   * | b  d ty  |
   * |_0  0  1 _|
   * </pre>
   * Creates a MMatrix for 2d affine transformations.
   *
   * concat, inverse, rotate, scale and translate return new matrices with the
   * transformations applied. The MMatrix is not modified in place.
   *
   * Returns the identity MMatrix when called with no arguments.
   * @name MMatrix
   * @param {Number} [a]
   * @param {Number} [b]
   * @param {Number} [c]
   * @param {Number} [d]
   * @param {Number} [tx]
   * @param {Number} [ty]
   * @constructor
   */
  function MMatrix(a, b, c, d, tx, ty) {
    a = a !== undefined ? a : 1;
    d = d !== undefined ? d : 1;

    return {
      /**
       * @name a
       * @fieldOf MMatrix#
       */
      a: a,
      /**
       * @name b
       * @fieldOf MMatrix#
       */
      b: b || 0,
      /**
       * @name c
       * @fieldOf MMatrix#
       */
      c: c || 0,
      /**
       * @name d
       * @fieldOf MMatrix#
       */
      d: d,
      /**
       * @name tx
       * @fieldOf MMatrix#
       */
      tx: tx || 0,
      /**
       * @name ty
       * @fieldOf MMatrix#
       */
      ty: ty || 0,

      /**
       * Returns the result of this MMatrix multiplied by another MMatrix
       * combining the geometric effects of the two. In mathematical terms, 
       * concatenating two MMatrixes is the same as combining them using MMatrix multiplication.
       * If this MMatrix is A and the MMatrix passed in is B, the resulting MMatrix is A x B
       * http://mathworld.wolfram.com/MMatrixMultiplication.html
       * @name concat
       * @methodOf MMatrix#
       *
       * @param {MMatrix} MMatrix The MMatrix to multiply this MMatrix by.
       * @returns The result of the MMatrix multiplication, a new MMatrix.
       * @type MMatrix
       */
      concat: function(MMatrix) {
        return MMatrix(
          this.a * MMatrix.a + this.c * MMatrix.b,
          this.b * MMatrix.a + this.d * MMatrix.b,
          this.a * MMatrix.c + this.c * MMatrix.d,
          this.b * MMatrix.c + this.d * MMatrix.d,
          this.a * MMatrix.tx + this.c * MMatrix.ty + this.tx,
          this.b * MMatrix.tx + this.d * MMatrix.ty + this.ty
        );
      },

      /**
       * Given a MPoint in the pretransform coordinate space, returns the coordinates of 
       * that MPoint after the transformation occurs. Unlike the standard transformation 
       * applied using the transformMPoint() method, the deltaTransformMPoint() method's 
       * transformation does not consider the translation parameters tx and ty.
       * @name deltaTransformMPoint
       * @methodOf MMatrix#
       * @see #transformMPoint
       *
       * @return A new MPoint transformed by this MMatrix ignoring tx and ty.
       * @type MPoint
       */
      deltaTransformMPoint: function(MPoint) {
        return MPoint(
          this.a * MPoint.x + this.c * MPoint.y,
          this.b * MPoint.x + this.d * MPoint.y
        );
      },

      /**
       * Returns the inverse of the MMatrix.
       * http://mathworld.wolfram.com/MMatrixInverse.html
       * @name inverse
       * @methodOf MMatrix#
       *
       * @returns A new MMatrix that is the inverse of this MMatrix.
       * @type MMatrix
       */
      inverse: function() {
        var determinant = this.a * this.d - this.b * this.c;
        return MMatrix(
          this.d / determinant,
          -this.b / determinant,
          -this.c / determinant,
          this.a / determinant,
          (this.c * this.ty - this.d * this.tx) / determinant,
          (this.b * this.tx - this.a * this.ty) / determinant
        );
      },

      /**
       * Returns a new MMatrix that corresponds this MMatrix multiplied by a
       * a rotation MMatrix.
       * @name rotate
       * @methodOf MMatrix#
       * @see MMatrix.rotation
       *
       * @param {Number} theta Amount to rotate in radians.
       * @param {MPoint} [aboutMPoint] The MPoint about which this rotation occurs. Defaults to (0,0).
       * @returns A new MMatrix, rotated by the specified amount.
       * @type MMatrix
       */
      rotate: function(theta, aboutMPoint) {
        return this.concat(MMatrix.rotation(theta, aboutMPoint));
      },

      /**
       * Returns a new MMatrix that corresponds this MMatrix multiplied by a
       * a scaling MMatrix.
       * @name scale
       * @methodOf MMatrix#
       * @see MMatrix.scale
       *
       * @param {Number} sx
       * @param {Number} [sy]
       * @param {MPoint} [aboutMPoint] The MPoint that remains fixed during the scaling
       * @type MMatrix
       */
      scale: function(sx, sy, aboutMPoint) {
        return this.concat(MMatrix.scale(sx, sy, aboutMPoint));
      },

      /**
       * Returns the result of applying the geometric transformation represented by the 
       * MMatrix object to the specified MPoint.
       * @name transformMPoint
       * @methodOf MMatrix#
       * @see #deltaTransformMPoint
       *
       * @returns A new MPoint with the transformation applied.
       * @type MPoint
       */
      transformMPoint: function(MPoint) {
        return MPoint(
          this.a * MPoint.x + this.c * MPoint.y + this.tx,
          this.b * MPoint.x + this.d * MPoint.y + this.ty
        );
      },

      /**
       * Translates the MMatrix along the x and y axes, as specified by the tx and ty parameters.
       * @name translate
       * @methodOf MMatrix#
       * @see MMatrix.translation
       *
       * @param {Number} tx The translation along the x axis.
       * @param {Number} ty The translation along the y axis.
       * @returns A new MMatrix with the translation applied.
       * @type MMatrix
       */
      translate: function(tx, ty) {
        return this.concat(MMatrix.translation(tx, ty));
      }
    };
  }

  /**
   * Creates a MMatrix transformation that corresponds to the given rotation,
   * around (0,0) or the specified MPoint.
   * @see MMatrix#rotate
   *
   * @param {Number} theta Rotation in radians.
   * @param {MPoint} [aboutMPoint] The MPoint about which this rotation occurs. Defaults to (0,0).
   * @returns 
   * @type MMatrix
   */
  MMatrix.rotation = function(theta, aboutMPoint) {
    var rotationMMatrix = MMatrix(
      Math.cos(theta),
      Math.sin(theta),
      -Math.sin(theta),
      Math.cos(theta)
    );

    if(aboutMPoint) {
      rotationMMatrix =
        MMatrix.translation(aboutMPoint.x, aboutMPoint.y).concat(
          rotationMMatrix
        ).concat(
          MMatrix.translation(-aboutMPoint.x, -aboutMPoint.y)
        );
    }

    return rotationMMatrix;
  };

  /**
   * Returns a MMatrix that corresponds to scaling by factors of sx, sy along
   * the x and y axis respectively.
   * If only one parameter is given the MMatrix is scaled uniformly along both axis.
   * If the optional aboutMPoint parameter is given the scaling takes place
   * about the given MPoint.
   * @see MMatrix#scale
   *
   * @param {Number} sx The amount to scale by along the x axis or uniformly if no sy is given.
   * @param {Number} [sy] The amount to scale by along the y axis.
   * @param {MPoint} [aboutMPoint] The MPoint about which the scaling occurs. Defaults to (0,0).
   * @returns A MMatrix transformation representing scaling by sx and sy.
   * @type MMatrix
   */
  MMatrix.scale = function(sx, sy, aboutMPoint) {
    sy = sy || sx;

    var scaleMMatrix = MMatrix(sx, 0, 0, sy);

    if(aboutMPoint) {
      scaleMMatrix =
        MMatrix.translation(aboutMPoint.x, aboutMPoint.y).concat(
          scaleMMatrix
        ).concat(
          MMatrix.translation(-aboutMPoint.x, -aboutMPoint.y)
        );
    }

    return scaleMMatrix;
  };

  /**
   * Returns a MMatrix that corresponds to a translation of tx, ty.
   * @see MMatrix#translate
   *
   * @param {Number} tx The amount to translate in the x direction.
   * @param {Number} ty The amount to translate in the y direction.
   * @return A MMatrix transformation representing a translation by tx and ty.
   * @type MMatrix
   */
  MMatrix.translation = function(tx, ty) {
    return MMatrix(1, 0, 0, 1, tx, ty);
  };

  /**
   * A constant representing the identity MMatrix.
   * @name IDENTITY
   * @fieldOf MMatrix
   */
  MMatrix.IDENTITY = MMatrix();
  /**
   * A constant representing the horizontal flip transformation MMatrix.
   * @name HORIZONTAL_FLIP
   * @fieldOf MMatrix
   */
  MMatrix.HORIZONTAL_FLIP = MMatrix(-1, 0, 0, 1);
  /**
   * A constant representing the vertical flip transformation MMatrix.
   * @name VERTICAL_FLIP
   * @fieldOf MMatrix
   */
  MMatrix.VERTICAL_FLIP = MMatrix(1, 0, 0, -1);
  
  // Export to window
  window["MPoint"] = MPoint;
  window["MMatrix"] = MMatrix;
}());