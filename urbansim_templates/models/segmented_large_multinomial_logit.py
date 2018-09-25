from __future__ import print_function

import copy

import numpy as np
import pandas as pd

import orca
from urbansim.models.util import apply_filter_query

from ..__init__ import __version__
from ..utils import update_name
from .. import modelmanager
from . import LargeMultinomialLogitStep


@modelmanager.template
class SegmentedLargeMultinomialLogitStep():
    """
    TO DO - finish documentation
    
    Generating submodels: 
    - The first time you run "build_submodels()" or "fit_all()", submodels will be 
      generated based on the `segmentation_column` and the current properties of the 
      `defaults` object.
    
    Accessing submodels: 
    - After they're generated, you can access the individual submodel objects through the 
      `submodels` property (list of LargeMultinomialLogitSteps).
    
    Editing a submodel: 
    - Feel free to modify individual submodels as desired.
    
    Editing all submodels: 
    - Changing a property of the `defaults` object will update that property for all of 
      the submodels, without affecting other customizations.
    
    Limitations: 
    - The submodels are implemented by applying filters to the choosers table. If a prior 
      filter exists, the submodel filters will be added to it.
        
    
    Parameters
    ----------
    defaults : LargeMultinomialLogitStep, optional
    
    segmentation_column : str, optional
        Name of a column containing categorical data. Should be found in the `choosers`
        table of the `defaults` object.
    
    name : str, optional
    
    tags : list of str, optional
    
    """
    def __init__(self, defaults=None, segmentation_column=None, name=None, tags=[]):
        
        if defaults is None:
            defaults = LargeMultinomialLogitStep()
        
        self.defaults = defaults
        self.defaults.bind_to(self.update_submodels)
        
        self.segmentation_column = segmentation_column
        
        self.name = name
        self.tags = tags
        
        self.template = self.__class__.__name__
        self.template_version = __version__
        
        # Properties to be filled in by build_submodels() or from_dict()
        self.submodels = {}
    
    
    @classmethod
    def from_dict(cls, d):
        """
        Create an object instance from a saved dictionary representation.
        
        Parameters
        ----------
        d : dict
        
        Returns
        -------
        SegmentedLargeMultinomialLogitStep
        
        """
        mnl_step = LargeMultinomialLogitStep.from_dict
        
        obj = cls(
            defaults = mnl_step(d['defaults']),
            segmentation_column = d['segmentation_column'],
            name = d['name'],
            tags = d['tags'])
        
        obj.submodels = {k: mnl_step(m) for k, m in d['submodels'].items()}
        
        return obj

    
    def to_dict(self):
        """
        Create a dictionary representation of the object.
        
        Returns
        -------
        dict
        
        """
        d = {
            'template': self.template,
            'template_version': self.template_version,
            'name': self.name,
            'tags': self.tags,
            'defaults': self.defaults.to_dict(),
            'segmentation_column': self.segmentation_column,
            'submodels': {k: m.to_dict() for k, m in self.submodels.items()}
        }
        return d
    
    
    def get_segmentation_column(self):
        """
        Get the segmentation column from Orca. Applies the overall chooser and 
        alternative filters and returns segmentation values for valid observations only.
        
        Returns
        -------
        pd.Series
        
        """
        # TO DO - this doesn't filter for columns in the model expression; is there
        #   centralized functionality for this merge that we should be using instead?
        
        obs = orca.get_table(self.defaults.choosers).to_frame()
        obs = apply_filter_query(obs, self.defaults.chooser_filters)
        
        alts = orca.get_table(self.defaults.alternatives).to_frame()
        alts = apply_filter_query(alts, self.defaults.alt_filters)

        df = pd.merge(obs, alts, how='inner', 
                      left_on=self.defaults.choice_column, right_index=True)
        
        return df[self.segmentation_column]
        
    
    def build_submodels(self):
        """
        Create a submodel for each category of choosers identified in the segmentation
        column. Running this method will overwrite any previous submodels. It can be run 
        as many times as desired.
        
        """
        self.submodels = {}
        submodel = LargeMultinomialLogitStep.from_dict(self.defaults.to_dict())

        col = self.get_segmentation_column()

        if (len(col) == 0):
            print("Warning: No valid observations after applying the chooser and "+
                  "alternative filters")
            return
        
        cats = col.astype('category').cat.categories.values

        print("Building submodels for {} categories: {}".format(len(cats), cats))
        
        for cat in cats:
            m = copy.deepcopy(submodel)
            seg_filter = "{} == '{}'".format(self.segmentation_column, cat)
            
            if isinstance(m.chooser_filters, list):
                m.chooser_filters += [seg_filter]
            
            elif isinstance(m.chooser_filters, str):
                m.chooser_filters = [m.chooser_filters, seg_filter]
            
            else:
                m.chooser_filters = seg_filter
            
            # TO DO - same for out_chooser_filters, once we handle simulation
            self.submodels[cat] = m
        
    
    def update_submodels(self, param, value):
        """
        Updates a property across all the submodels. This method is bound to the 
        `defaults` object and runs automatically when one of its properties is changed.
        
        The `chooser_filters` property cannot currently be updated this way, because it 
        could affect the model segmentation.
        
        Parameters
        ----------
        param : str
            Property name.
        value : anything
        
        """
        if (param == 'chooser_filters') & (len(self.submodels) > 0):
            print("Warning: Changing 'chooser_filters' can affect the model " +
                  "segmentation. Changes have been saved to 'defaults' but not to the " +
                  "submodels. To regenerate them using the new defaults, run " +
                  "'build_submodels()'.")
            return
        
        for k, m in self.submodels.items():
            setattr(m, param, value)
    
    
    def fit_all(self):
        """
        Fit all the submodels. Build the subomdels first, if they don't exist yet. This 
        method can be run as many times as desired.
        
        """
        if (len(self.submodels) == 0):
            self.build_submodels()
        
        for k, m in self.submodels.items():
            m.fit()
        
        self.name = update_name(self.template, self.name)
    
    
    def run(self):
        """
        Convenience method (requied by template spec) that invokes `run_all()`.
        
        """
        self.run_all()
    
    
    def run_all(self):
        """
        Not yet implemented.
        
        """
        pass