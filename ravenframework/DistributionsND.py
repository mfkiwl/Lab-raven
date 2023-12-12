# Copyright 2017 Battelle Energy Alliance, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Created on Nov 22, 2023
@author: j-bryan
"""

import numpy as np
import scipy.stats
import scipy.linalg

from .utils import mathUtils


class NDDistribution:
  """ Base class for multivariate distributions """
  def __init__(self):
    """
      Constructor

      @ In, None
      @ Out, None
    """
    self.dimensionality : int = None
    self.lowerBounds : list = None
    self.upperBounds : list = None

  def returnDimensionality(self):
    """
      Return the dimensionality of the distribution

      @ In, None
      @ Out, dimensionality, int, the dimensionality of the distribution
    """
    return self.dimensionality

  def returnLowerBound(self, dim):
    """
      Return the lower bound of the distribution for the given dimension

      @ In, dim, int, the dimension
      @ Out, lowerBound, float, the lower bound
    """
    lowerBound = self.lowerBounds[dim]
    return lowerBound

  def returnUpperBound(self, dim):
    """
      Return the upper bound of the distribution for the given dimension

      @ In, dim, int, the dimension
      @ Out, upperBound, float, the upper bound
    """
    upperBound = self.upperBounds[dim]
    return upperBound

class MultivariateNormalPCA(NDDistribution):
  """ A PCA-based multivariate normal distribution """
  def __init__(self, cov, mean, covType='abs', rank=None):
    """
      Constructor

      @ In, cov, np.ndarray, the covariance matrix
      @ In, mean, np.ndarray, the mean vector
      @ In, covType, string, optional, the type of covariance matrix provided. May be 'abs' or 'rel'.
      @ In, rank, int, optional, the reduced dimension
      @ Out, None
    """
    super().__init__()
    self.dimensionality = len(mean)

    cov = np.array(cov).reshape((self.dimensionality, self.dimensionality))
    covSymmetric = 0.5 * (cov + cov.T)  # make sure it is symmetric
    self._covariance = covSymmetric
    self._covarianceType = covType

    self._mu = np.asarray(mean)
    self._rank = len(mean) if rank is None else rank
    if self._rank > len(mean):
      raise ValueError("The provided rank is larger than the given problem's dimension, it should be less or equal!")

    self.lowerBounds, self.upperBounds = self._calculateDefaultBounds(self._mu, self._covariance)

    # Use singular value decomposition to compute the transformation matrix
    U, s, V = mathUtils.computeTruncatedSingularValueDecomposition(covSymmetric, self._rank)
    U, V = mathUtils.correctSVDSigns(U, V)

    # Compute S^(1/2) and S^(-1/2) matrices, allowing for zero singular values
    SqrtS = np.diag(s ** 0.5)
    sZero = s == 0
    sRecipSqrt = 1 / np.sqrt(s)
    sRecipSqrt[sZero] = 0
    SqrtSRecip = np.diag(sRecipSqrt)

    self._colorize = U @ SqrtS  # forward transform
    self._whiten = SqrtSRecip @ U.T  # inverse transform
    self._singularValues = s

    # scipy distribution objects for calculating pdf and cdf
    # FIXME this doesn't seem to handle singular matrices correctly
    self._unitMVNorm = scipy.stats.multivariate_normal(np.zeros(self._rank), np.eye(self._rank))
    self._marginal = scipy.stats.norm(0, 1)  # unit normal distribution is the marginal

  def _calculateDefaultBounds(self, mu, cov):
    """
      Sets the default bounds for the distribution to be +/- 6 standard deviations about the mean

      @ In, mu, np.ndarray, the mean vector
      @ In, cov, np.ndarray, the covariance matrix
      @ Out, (lowerBounds, upperBounds), tuple, the lower and upper bounds
    """
    nDiscretizations = int(1e-4 ** (-1 / self.dimensionality) + 0.5)
    std = np.sqrt(np.diag(cov))
    deltaSigma = 12 * std / nDiscretizations

    lowerBounds = mu - 6 * std
    upperBounds = lowerBounds + deltaSigma * (nDiscretizations - 1)
    return (lowerBounds, upperBounds)

  def pdf(self, x):
    """
      Probability density function

      @ In, x, np.ndarray, the coordinates where the pdf needs to be evaluated
      @ Out, pdf, float, the pdf value
    """
    print('pdf')
    xTrans = self.coordinateTransformed(x)
    pdf = self.pdfInTransformedSpace(xTrans)
    return pdf

  def pdfInTransformedSpace(self, x):
    """
      Probability density function in the PCA space

      @ In, x, np.ndarray, the coordinates where the pdf needs to be evaluated
      @ Out, pdf, float, the pdf value
    """
    print('pdfInTransformedSpace')
    pdf = self._unitMVNorm.pdf(x)
    return pdf

  def cdf(self, x):
    """
      Cumulative distribution function

      @ In, x, np.ndarray, the coordinates where the cdf needs to be evaluated
      @ Out, cdf, float, the cdf value
    """
    print('cdf')
    xTrans = self.coordinateTransformed(x)
    cdf = self._unitMVNorm.cdf(xTrans)
    return cdf

  def getTransformationMatrix(self, coordinateIndex=None):
    """
      Get the transformation matrix (colorizing matrix) for the given coordinate index, if provided

      @ In, coordinateIndex, list, optional, the coordinate index
      @ Out, transformationMatrix, np.ndarray, the transformation matrix
    """
    transMatrix = self._colorize[:, coordinateIndex] if coordinateIndex else self._colorize
    return transMatrix

  def getInverseTransformationMatrix(self, coordinateIndex=None):
    """
      Get the inverse transformation matrix (whitening matrix) for the given coordinate index, if provided

      @ In, coordinateIndex, list, optional, the coordinate index
      @ Out, invTransMatrix, np.ndarray, the inverse transformation matrix
    """
    invTransMatrix = self._whiten[coordinateIndex, :] if coordinateIndex else self._whiten
    return invTransMatrix

  def getSingularValues(self, coordinateIndex=None):
    """
      Get the singular values for the given coordinate index, if provided

      @ In, coordinateIndex, list, optional, the coordinate index
      @ Out, singularValues, np.ndarray, the singular values
    """
    singularValues = self._singularValues[coordinateIndex] if coordinateIndex else self._singularValues
    return singularValues

  def coordinateTransformed(self, coordinate):
    """
      Transform the coordinates from the original space to the white PCA space

      @ In, coordinate, np.ndarray, the coordinates in the original space
      @ Out, coordTrans, np.ndarray, the coordinates in the white PCA space
    """
    print('coordinateTransformed')
    if self._covarianceType == 'abs':
      coordTrans = (coordinate - self._mu) @ self._whiten.T
    else:
      coordTrans = (coordinate / self._mu - 1) @ self._whiten.T
    return coordTrans

  def coordinateInverseTransformed(self, coordinate, coordinateIndex=None):
    """
      Transform the coordinates from the white PCA space to the colored original space

      @ In, coordinate, np.ndarray, the coordinates in the whitened PCA space
      @ In, coordinateIndex, list, optional, the coordinate index
      @ Out, coordInvTrans, np.ndarray, the coordinates in the colored original space
    """
    print('coordinateInverseTransformed')
    if self._covarianceType == 'abs':
      coordInvTrans = coordinate @ self._colorize.T + self._mu
    else:
      coordInvTrans = (coordinate @ self._colorize.T + 1) * self._mu

    if coordinateIndex is not None:
      coordInvTrans = coordInvTrans[coordinateIndex]

    return coordInvTrans

  def cellProbabilityWeight(self, center, dxs):
    """
      Compute the probability of a cell in the transformed space

      @ In, center, np.ndarray, the center of the cell
      @ In, dxs, np.ndarray, the widths of the cell in each dimension
      @ Out, probability, float, the probability weight of the cell
    """
    print('cellProbabilityWeight')
    dxMatrix = 0.5 * np.diag(dxs)
    coordinates = np.tile(center, (len(center), 1))
    upperCdf = self._marginal.cdf(coordinates + dxMatrix)
    lowerCdf = self._marginal.cdf(coordinates - dxMatrix)
    probability = np.prod(np.diagonal(upperCdf - lowerCdf))
    return probability

  def marginalCdfForPCA(self, x):
    """
      Compute the marginal cdf in the PCA space

      @ In, x, float, the coordinate
      @ Out, cdf, float, the marginal cdf value
    """
    print('marginalCdfForPCA')
    cdf = self._marginal.cdf(x)
    return cdf

  def inverseMarginalForPCA(self, x):
    """
      Compute the inverse marginal cdf in the PCA space

      @ In, x, float, the coordinate (between 0 and 1)
      @ Out, inverseCdf, float, the inverse marginal cdf value
    """
    print('inverseMarginalForPCA')
    inverseCdf = self._marginal.ppf(x)
    return inverseCdf
