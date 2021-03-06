import copy
import os
from typing import Optional, Sequence
from configargparse import Namespace

from pydpiper.minc.conversion import generic_converter
from pydpiper.minc.files import ToMinc
from pydpiper.minc.nlin import Algorithms
from pydpiper.core.stages import Result, CmdStage, Stages
from pydpiper.core.files  import ImgAtom, FileAtom


# TODO delete ITK prefix?
class ITKXfmAtom(FileAtom):
    pass

class ITKImgAtom(ImgAtom):
    pass


def convert(infile : ImgAtom, out_ext : str) -> Result[ImgAtom]:
    s = Stages()
    outfile = infile.newext(ext=out_ext)
    if infile.mask is not None:
        outfile.mask = s.defer(convert(infile.mask, out_ext=out_ext))
    if infile.labels is not None:
        outfile.mask = s.defer(convert(infile.labels, out_ext=out_ext))
    s.add(CmdStage(inputs=(infile,), outputs=(outfile,),
                   cmd = ['c3d', infile.path, '-o', outfile.path]))
    return Result(stages=s, output=outfile)


def itk_convert_xfm(xfm : ITKXfmAtom, out_ext : str) -> Result[ITKXfmAtom]:
    if xfm.ext == out_ext:
        return Result(stages=Stages(), output=xfm)
    else:
        out_xfm = xfm.newext(out_ext)
        cmd = CmdStage(inputs=(xfm,), outputs=(out_xfm,),
                       cmd=["itk_convert_xfm", "--clobber", xfm.path, out_xfm.path])
        return Result(stages=Stages((cmd,)), output=out_xfm)


# TODO 'ITK' seems like a weird place for these; probably belong in minc;
# also, 'generic_converter' is - did I mention? - generic
mnc2nii = generic_converter(renamer = lambda img: img.newext(".nii"),
                            mk_cmd = lambda i, o: ["bash", "-c", "'rm %s.path; mnc2nii %s %s'" % (o, i, o)])

nii2mnc = generic_converter(renamer = lambda img: img.newext(".mnc"),
                            mk_cmd = lambda i, o: "nii2mnc -clobber {i} {o}".split())


class Interpolation(object):
    def render(self):
        return self.__class__.__name__

class Linear(Interpolation): pass
class NearestNeighbor(Interpolation): pass
class MultiLabel(Interpolation):  """TODO: add options"""
class Gaussian(Interpolation): """TODO: add options"""
class BSpline(Interpolation):
    def __init__(self, order=None):
        self.order = order
    def render(self):
        return self.__class__.__name__ + (("[order=%d]" % self.order) if self.order is not None else "")
class CosineWindowsSinc(Interpolation): pass
class WelchWindowedSinc(Interpolation): pass
class HammingWindowedSinc(Interpolation): pass
class LanczosWindowedSinc(Interpolation): pass


def as_deformation(transform, reference_image, interpolation: Interpolation = None,
                   invert: bool = None, dimensionality: int = None,
                   default_voxel_value: float = None, new_name_wo_ext: str = None,
                   subdir: str = None, ext: str = None) -> Result[ITKImgAtom]:
    """Convert an arbitrary ITK transformation to a deformation field representation.
    Consider this an image rather than a transformation since, e.g., AverageImages can be used."""

    if not subdir:
        subdir = 'tmp'

    ext = ext or ".nii.gz"

    if not new_name_wo_ext:
        out_xfm = xfmToImage(transform.newname(name=transform.filename_wo_ext + '_def', subdir=subdir, ext=ext))
    else:
        out_xfm = xfmToImage(transform.newname(name=new_name_wo_ext, subdir=subdir, ext=ext))

    # TODO add rest of --output options
    cmd = (["antsApplyTransforms",
            "--reference-image", reference_image.path,
            "--output", "[%s,1]" % out_xfm.path]
           + (["--transform", transform.path] if invert is None
              else ["-t", "[%s,%d]" % (transform.path, invert)])
           + (["--dimensionality", dimensionality] if dimensionality is not None else [])
           + (["--interpolation", interpolation.render()] if interpolation is not None else [])
           + (["--default-voxel-value", str(default_voxel_value)] if default_voxel_value is not None else []))
    s = CmdStage(cmd=cmd,
                 inputs=(transform, reference_image),
                 outputs=(out_xfm,))
    return Result(stages=Stages([s]), output=out_xfm)


# TODO: generalize to multiple transforms (see program name)
def antsApplyTransforms(img,
                        transform,
                        reference_image,
                        #outfile: str = None,
                        interpolation: Interpolation = None,
                        invert: bool = None,
                        dimensionality: int = None,
                        input_image_type = None,
                        output_warped_file: bool = None,
                        default_voxel_value: float = None,
                        #static_case_for_R: bool = None,
                        #float: bool = None
                        new_name_wo_ext: str = None,
                        subdir: str = None):

    if not subdir:
        subdir = 'resampled'

    if not new_name_wo_ext:
        out_img = img.newname(name=transform.filename_wo_ext + '-resampled', subdir=subdir)
    else:
        out_img = img.newname(name=new_name_wo_ext, subdir=subdir)

    # TODO add rest of --output options
    cmd = (["antsApplyTransforms",
            "--input", img.path,
            "--reference-image", reference_image.path,
            "--output", out_img.path]
           + (["--transform", transform.path] if invert is None
              else ["-t", "[%s,%d]" % (transform.path, invert)])
           + (["--dimensionality", dimensionality] if dimensionality is not None else [])
           + (["--interpolation", interpolation.render()] if interpolation is not None else [])
           + (["--default-voxel-value", str(default_voxel_value)] if default_voxel_value is not None else []))
    s = CmdStage(cmd=cmd,
                 inputs=(img, transform, reference_image),
                 outputs=(out_img,))
    return Result(stages=Stages([s]), output=out_img)


def resample_simple(img, xfm, like,
                    invert = False,
                    use_nn_interpolation = None,
                    new_name_wo_ext = None,
                    subdir = None,
                    postfix = None):
    return antsApplyTransforms(img=img, transform=xfm, reference_image=like,
                               interpolation=MultiLabel() if use_nn_interpolation else None,
                               invert=invert, new_name_wo_ext=new_name_wo_ext, subdir=subdir)


def resample(img,
             xfm,  # TODO: update to handler?
             like,
             invert = False,
             use_nn_interpolation = None,
             new_name_wo_ext: str = None,
             subdir: str = None,
             postfix: str = None):

    s = Stages()

    if not subdir:
        subdir = 'resampled'

    # we need to get the filename without extension here in case we have
    # masks/labels associated with the input file. When that's the case,
    # we supply its name with "_mask" and "_labels" for which we need
    # to know what the main file will be resampled as
    if not new_name_wo_ext:
        # FIXME this is wrong when invert=True
        new_name_wo_ext = xfm.filename_wo_ext + '-resampled'

    new_img = s.defer(resample_simple(img=img, xfm=xfm, like=like,
                                      invert=invert,
                                      use_nn_interpolation=use_nn_interpolation,
                                      new_name_wo_ext=new_name_wo_ext,
                                      subdir=subdir))
    new_img.mask = s.defer(resample_simple(img=img.mask, xfm=xfm, like=like,
                                           use_nn_interpolation=True,
                                           invert=invert,
                                           new_name_wo_ext=new_name_wo_ext + "_mask",
                                           subdir=subdir)) if img.mask is not None else None
    new_img.labels = s.defer(resample_simple(img=img.labels, xfm=xfm, like=like,
                                             use_nn_interpolation=True,
                                             invert=invert,
                                             new_name_wo_ext=new_name_wo_ext + "_labels",
                                             subdir=subdir)) if img.labels is not None else None

    # Note that new_img can't be used for anything until the mask/label files are also resampled.
    # This shouldn't create a problem with stage dependencies as long as masks/labels appear in inputs/outputs of CmdStages.
    # (If this isn't automatic, a relevant helper function would be trivial.)
    # TODO: can/should this be done semi-automatically? probably ...
    return Result(stages=s, output=new_img)


# is c3d or ImageMath better for this (memory)?
def max(imgs : Sequence[ImgAtom], out_img : ImgAtom):
    cmd = CmdStage(inputs = imgs, outputs = (out_img,),
                   cmd = (['c3d'] + [img.path for img in imgs]
                          + ['-accum', '-max', '-endaccum', '-o', out_img.path]))
    return Result(stages=Stages((cmd,)), output=out_img)


def average_images(imgs        : Sequence[ImgAtom],
                   dimensions  : int = 3,
                   normalize   : bool = False,
                   output_dir  : str = '.',
                   name_wo_ext : str = "average",
                   out_ext     : Optional[str] = None,
                   avg_file    : Optional[ITKImgAtom] = None) -> Result[ITKImgAtom]:

    s = Stages()

    if len(imgs) == 0:
        raise ValueError("`AverageImages` arg `imgs` is empty (can't average zero files)")

    ext = out_ext or imgs[0].ext

    # the output_dir basically gives us the equivalent of the pipeline_sub_dir for
    # regular input files to a pipeline, so use that here
    avg = avg_file or ImgAtom(name=os.path.join(output_dir, '%s.todo' % name_wo_ext),
                              orig_name=None,
                              pipeline_sub_dir=output_dir)
    avg.ext = ext

    # if all input files have masks associated with them, add the combined mask to
    # the average:
    # TODO what if avg_file has a mask ... should that be used instead? (then rename avg -> avg_file above)
    all_inputs_have_masks = all((img.mask for img in imgs))
    if all_inputs_have_masks:
        combined_mask = (ImgAtom(name=os.path.join(avg_file.dir, '%s_mask.todo' % avg_file.filename_wo_ext),
                                 orig_name=None,
                                 pipeline_sub_dir=avg_file.pipeline_sub_dir)
                         if avg_file is not None else
                         ImgAtom(name=os.path.join(output_dir, '%s_mask.todo' % name_wo_ext),
                                 orig_name=None,
                                 pipeline_sub_dir=output_dir))
        combined_mask.ext = ext
        s.defer(max(imgs=sorted({img_inst.mask for img_inst in imgs}),
                    out_img=combined_mask))
        avg.mask = combined_mask
    s.add(CmdStage(inputs = imgs,
                   outputs = (avg,),
                   cmd = ["AverageImages", str(dimensions), avg.path, "%d" % normalize]
                         + [img.path for img in imgs]))
    return Result(stages=s, output=avg)


class ToMinc(ToMinc):
    @staticmethod
    def to_mnc(img): return convert(img, out_ext=".mnc")
    @staticmethod
    def from_mnc(img): return convert(img, out_ext=".nii.gz")
    @staticmethod
    def to_mni_xfm(xfm): return itk_convert_xfm(xfm, out_ext=".mnc")
    @staticmethod
    def from_mni_xfm(xfm): return itk_convert_xfm(xfm, out_ext=".nii.gz")

def imageToXfm(i : ITKImgAtom) -> ITKXfmAtom:
    x = copy.deepcopy(i)
    x.__class__ = ITKXfmAtom
    del x.mask
    del x.labels
    return x

def xfmToImage(x : ITKXfmAtom):
    i = copy.deepcopy(x)
    i.__class__ = ITKImgAtom
    i.mask = None
    i.labels = None
    return i

# TODO move this
class Algorithms(Algorithms):
    average   = average_images
    @staticmethod
    def blur(img, fwhm, gradient=True, subdir='tmp'):
        # note c3d can take voxel rather than fwhm specification, but the Algorithms interface
        # currently doesn't allow this to be used ... maybe an argument from switching from mincblur
        if fwhm in (-1, 0, None):
            if gradient:
                raise ValueError("can't compute gradient without a positive FWHM")
            return Result(stages=Stages(), output=Namespace(img=img))

        if gradient:
            out_gradient = img.newname_with("_blur%s_grad" % fwhm)
        else:
            out_gradient = None

        out_img = img.newname_with("_blurred%s" % fwhm)

        cmd = CmdStage(cmd=['c3d', '-smooth', "%smm" % fwhm, '-o', out_img.path, img.path]
                           + (['-gradient', '-o', out_gradient.path] if gradient else []),
                       inputs=(img), outputs=(out_img, out_gradient) if gradient else (out_img,))
        return Result(stages=Stages((cmd,)),
                      output=Namespace(img=out_img, gradient=out_gradient)
                               if gradient else Namespace(img=out_img))

    resample = resample

    @staticmethod
    def scale_transform(xfm, scale, newname_wo_ext):
        s = Stages()
        defs = s.defer(as_deformation(transform=xfm.xfm, reference=xfm.source))
        scaled_defs = (defs.xfm.newname(newname_wo_ext) if newname_wo_ext else
                        defs.xfm.newname_with_suffix("_scaled_%s" % scale))
        s.defer(CmdStage(cmd=['c3d', '-scale', str(scale), defs.path, "-o", scaled_defs.path],
                         inputs=(defs,), outputs=(scaled_defs,)))
        return Result(stages=s, output=scaled_defs)

    @staticmethod
    def average_transforms(xfms, avg_xfm):
        s = Stages()
        defs = [s.defer(as_deformation(transform=xfm.xfm, reference_image=xfm.source)) for xfm in xfms]
        #avg_img = NotImplemented
        avg = imageToXfm(s.defer(average_images(defs,
                                                avg_file=xfmToImage(avg_xfm),
                                                #output_dir=os.path.join(defs[0].pipeline_sub_dir,
                                                #                        defs[0].output_sub_dir,
                                                #                        "transforms")
                                                )))
        return Result(stages=s, output=avg)