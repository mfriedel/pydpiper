
from abc import ABCMeta, abstractclassmethod, abstractstaticmethod
from typing import List, Generic, TypeVar, Optional, Sequence

from pydpiper.core.stages import Result
from pydpiper.minc.containers import GenericXfmHandler
from pydpiper.minc.files import MincAtom, ImgAtom, ToMinc

I = TypeVar('I', bound=ImgAtom)
X = TypeVar('X')


class Algorithms(Generic[I, X], metaclass=ABCMeta):
    @abstractstaticmethod
    def blur(img : I,
             fwhm : float,
             gradient : bool = True,
             subdir : str = "tmp"):
        pass

    @abstractstaticmethod
    def average(imgs : Sequence[I],
                output_dir : str = '.',
                name_wo_ext : str = "average",
                avg_file : I = None) -> Result[I]:
        pass

    @abstractstaticmethod
    def resample(img: I,
                 xfm: X,  # TODO: update to handler?
                 like: I,
                 invert: bool = False,
                 use_nn_interpolation : Optional[bool] = None,
                 #interpolation = None,   #interpolation: Interpolation = None,
                 #  TODO fix type for non-minc resampling programs; also, can't import Interpolation here
                 #extra_flags: Sequence[str] = (),
                 new_name_wo_ext: str = None,
                 subdir: str = None,
                 postfix: str = None) -> Result[I]:
        pass

    # must be able to handle arbitrary (not simply pure linear or pure nonlinear) transformations.
    # we should have a separate method for averaging purely affine transformations.
    # also, we should track whether or not a transform is pure affine (either by inspecting it
    # or via additional metadata in pydpiper) in order to use this more efficient functionality when possible
    @abstractstaticmethod
    def average_transforms(xfms : Sequence[GenericXfmHandler[I, X]], avg_xfm : I) -> X: pass
    # TODO: it seems a bit heavyweight to require XfmHandlers here simply for sampling purposes

    @abstractstaticmethod
    # a bit weird that this takes and XfmH but returns an XfmA, but the extra image data is used for sampling
    def scale_transform(xfm : Sequence[GenericXfmHandler[I, X]],
                        newname_wo_ext : str, scale : float) -> X: pass

    #def concat_xfms(): pass
    #def invert_xfm(): pass




# TODO not *actually* generic; should take a type as a field, but this is annoying to write down
class NLIN(Generic[I, X], metaclass=ABCMeta):
#class NLIN(metaclass=ABCMeta):
  class Conf: pass

  class MultilevelConf: pass

  class ToMinc(ToMinc): pass

  class Algorithms(Algorithms): pass

  @abstractstaticmethod
  def hierarchical_to_single(m: 'MultiLevelConf') -> Sequence[Conf]: pass

  @abstractstaticmethod
  def get_default_conf(resolution) -> Optional[Conf]: pass

  @abstractstaticmethod
  def get_default_multilevel_conf(resolution) -> Optional[MultilevelConf]: pass

  @abstractclassmethod
  def parse_protocol_file(cls, filename : str, resolution : float): pass

  # you might think it's odd to have this here, since it's not used by `register`,
  # but we want all NLIN classes to be usable for model building, and while we
  # could just give a default implementation in NLIN_BUILD_MODEL,
  # it seems a bit easier just to make the user supply it here (particularly since it can always be done,
  # and we've already implemented for minctracc, ANTS)
  @abstractclassmethod
  def parse_multilevel_protocol_file(cls, filename : str, resolution : float): pass

  @abstractstaticmethod
  def accepts_initial_transform(): pass

  @abstractclassmethod
  def register(cls,
               source : I,
               target : I,
               conf : Conf,
               resample_source : bool,
               resample_subdir : str,
               transform_name_wo_ext : str = None,
               initial_source_transform : Optional[I] = None): pass



class NLIN_BUILD_MODEL(NLIN, metaclass=ABCMeta):

    class BuildModelConf(): pass

    @abstractstaticmethod
    def build_model(imgs     : List[MincAtom],
                    conf     : BuildModelConf,
                    nlin_dir : str,
                    nlin_prefix : str,
                    initial_target : I,
                    #mincaverage,
                    output_name_wo_ext : Optional[str] = None): pass

    @abstractstaticmethod
    def parse_build_model_protocol(filename : str, resolution : float) -> BuildModelConf: pass

    @abstractstaticmethod
    def get_default_build_model_conf() -> BuildModelConf: pass
