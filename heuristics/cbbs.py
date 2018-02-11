import logging
import pprint
lgr = logging.getLogger(__name__)


def create_key(template, outtype=('nii.gz',), annotation_classes=None):
    if template is None or not template:
        raise ValueError('Template must be a valid format string')

    return template, outtype, annotation_classes


def get_study_spec():
    from os import environ
    import json
    filename = environ.get('CBBS_STUDY_SPEC')
    if filename:
        return json.load(open(filename, 'r'))
    else:
        return []

_study_spec = get_study_spec()
pprint.pprint(_study_spec)


# TODO
# Note: That doesn't work yet.
# Don't get it. seqinfos is coming in prefilled from dicom. So, what's the
# point in requiring this function? Apart from that shortly after heudiconv
# crashes with dict not hashable. Sth is wrong here.
# def infotoids(seqinfos, outdir):
#     # needed if we don't want to specify subject ids on command line
#     # would need to return sth like this (see dbic_bids):
#     # {
#     # # TODO: request info on study from the JedCap
#     # 'locator': locator,
#     # # Sessions to be deduced yet from the names etc TODO
#     # 'session': session,
#     # 'subject': subject,
#     # }
#     # Not sure, whether it is sufficient to provide kw 'subject' only
#     # TODO: "session"? A single one? Is this "the other session"?
#     subject = set(s['subject']['value'] for s in _study_spec)
#     if len(subject) == 1:
#         return {'locator': '',
#                 'session': None,
#                 'subject': subject}
#     else:
#         lgr.warning("Found %s candidates for 'subject': %s" %
#                     (len(subject), subject))
#         return {}


def infotodict(seqinfo):
    """Heuristic evaluator for determining which runs belong where

    allowed template fields - follow python string module:

    item: index within category
    subject: participant id
    seqitem: run number during scanning
    subindex: sub index within group
    """

    info = dict()
    for idx, s in enumerate(seqinfo):

        # find in spec:
        candidates = [series for series in _study_spec
                      if str(s.uid) == series['uid']]
        if not candidates:
            print("No candidates")
            print("Skip idx: %s" % idx)
            print("s.uid was: %s" % s.uid)
            lgr.warning("Found no match for seqinfo: %s" % str(s))
            continue
        if len(candidates) != 1:
            print("Multiple candidates")
            print("Skip idx: %s" % idx)
            print("s.uid was: %s" % s.uid)
            lgr.warning("Found %s match(es) for series UID %s" %
                        (len(candidates), s.uid))
            continue
        print("Processing idx: %s" % idx)
        series_spec = candidates[0]

        # subject
        if not series_spec['subject']['value']:
            lgr.warning("Found no subject in specification for series %s" % series_spec['uid'])

        dirname = filename = "sub-{}".format(series_spec['subject']['value'])
        # session
        if series_spec['session']:
            dirname += "/ses-{}".format(series_spec['session']['value'])
            filename += "_ses-{}".format(series_spec['session']['value'])

        # data type
        # TODO: not in spec yet. Anything to derive from?
        # Additional options according to BIDS: anat, dwi, fmap
        # Note: Yarik uses such a mapping: should/could we too? (dbic_bids)
        # image_data_type = s.image_type[2]
        # image_type_seqtype = {
        #     'P': 'fmap',   # phase
        #     'FMRI': 'func',
        #     'MPR': 'anat',
        #     # 'M': 'func',  "magnitude"  -- can be for scout, anat, bold, fmap
        #     'DIFFUSION': 'dwi',
        #     'MIP_SAG': 'anat',  # angiography
        #     'MIP_COR': 'anat',  # angiography
        #     'MIP_TRA': 'anat',  # angiography
        # }.get(image_data_type, None)

        data_type = 'func'
        dirname += "/{}".format(data_type)
        if data_type == 'func':
            # func/sub-<participant_label>[_ses-<session_label>]
            # _task-<task_label>[_acq-<label>][_rec-<label>][_run-<index>][_echo-<index>]_bold.nii[.gz]
            if series_spec['task']['value']:
                filename += "_task-{}".format(series_spec['task']['value'])

            # TODO: [_acq-<label>][_rec-<label>]

            if series_spec['run']['value']:
                filename += "_run-{}".format(series_spec['run']['value'])

            filename += "_bold"

        if data_type == 'anat':
            # anat/sub-<participant_label>[_ses-<session_label>]
            # [_acq-<label>][_ce-<label>][_rec-<label>][_run-<index>][_mod-<label>]_<modality_label>.nii[.gz]

            # TODO: [_acq-<label>][_ce-<label>][_rec-<label>]

            if series_spec['run']['value']:
                filename += "_run-{}".format(series_spec['run']['value'])

            # TODO: [_mod-<label>]_<modality_label>

        # TODO: data_type: dwi, fmap

        key = create_key(dirname + '/' + filename)
        if key not in info:
            info[key] = []

        info[key].append(s[2])

    return info
