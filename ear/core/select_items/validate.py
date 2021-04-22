from ...fileio.adm.elements import AudioPackFormat, AudioChannelFormat, TypeDefinition, ObjectCartesianPosition
from ...fileio.adm.exceptions import AdmError
from . import matrix
from .utils import in_by_id, pack_format_channels, pack_format_packs, pack_format_paths_from


def _validate_loops(type_name, nodes, get_children):
    """Check for loops in a structure which should be tree-like.

    Parameters:
        type_name (str): type of relationship to include in the error message
        nodes (list of object): nodes to start the search from
        get_children (function from node to list of nodes): function to call to
            get the list of children of a given node
    """
    # node id()s which have been visited by the DFS; at the end of each
    # top-level DFS call, all loops which can be found from nodes in visited
    # have already been found
    visited = set()

    def dfs(node, path):
        if in_by_id(node, path):
            raise AdmError("loop detected in {type_name}: {path}".format(
                type_name=type_name,
                path=' -> '.join(o.id for o in path + (node,))))

        if id(node) in visited:
            return
        visited.add(id(node))

        path = path + (node,)

        for child in get_children(node):
            dfs(child, path)

    for node in nodes:
        dfs(node, ())


def _validate_object_loops(adm):
    """Check for loops in the audioObject reference structure."""
    return _validate_loops("audioObjects", adm.audioObjects, lambda audioObject: audioObject.audioObjects)


def _validate_pack_channel_multitree(adm):
    """Check that audioPackFormat->audioPackFormat and
    audioPackFormat->audioChannelFormat references form a multitree; from each
    node, the accessible nodes should form a tree (i.e. each node should only
    be accessible via one path).
    """

    def get_children(node):
        if isinstance(node, AudioPackFormat):
            return node.audioPackFormats + node.audioChannelFormats
        else:
            return []

    def loop_exception(path):
        node = path[-1]
        node_idx = [id(n) for n in path[:-1]].index(id(node))
        loop_path = path[node_idx:]

        raise AdmError("loop detected in audioPackFormats: {path}".format(
            path=' -> '.join("'{n.id}'".format(n=n) for n in loop_path),
        ))

    def diamond_exception(node, path_a, path_b):
        common_parent_in_a = max(i for i, n in enumerate(path_a[:-1]) if in_by_id(n, path_b[:-1]))
        common_parent = path_a[common_parent_in_a]
        common_parent_in_b = max(i for i, n in enumerate(path_b[:-1]) if n is common_parent)

        path_a = path_a[common_parent_in_a:]
        path_b = path_b[common_parent_in_b:]

        type_names = {
            AudioPackFormat: "audioPackFormat",
            AudioChannelFormat: "audioChannelFormat",
        }

        if len(path_a) == 2 and len(path_b) == 2:
            message = ("{node_type} '{node.id}' is included more than once in "
                       "{common_parent_type} '{common_parent.id}'")
        else:
            message = ("{node_type} '{node.id}' is included more than once in "
                       "{common_parent_type} '{common_parent.id}' via paths {path_a} and {path_b}")

        raise AdmError(message.format(
            node=node,
            node_type=type_names[type(node)],
            common_parent=common_parent,
            common_parent_type=type_names[type(common_parent)],
            path_a=" -> ".join("'{n.id}'".format(n=n) for n in path_a),
            path_b=" -> ".join("'{n.id}'".format(n=n) for n in path_b),
        ))

    def dfs(node, paths, path):
        path = path + (node,)

        # check if there are any loops. This would also be caught by
        # `if id(node) in paths` below, but we can make a nicer error message
        # in this case.
        if in_by_id(node, path[:-1]):
            loop_exception(path)

        if id(node) in paths:
            path_a, path_b = paths[id(node)], path
            diamond_exception(node, path_a, path_b)

        paths[id(node)] = path
        for child in get_children(node):
            dfs(child, paths, path)

    for node in adm.audioPackFormats:
        dfs(node, {}, ())


def _validate_pack_channel_types(adm):
    """Check that pack formats only contain channel formats of their specified type."""
    for audioPackFormat in adm.audioPackFormats:
        for audioChannelFormat in audioPackFormat.audioChannelFormats:
            if audioChannelFormat.type != audioPackFormat.type:
                raise AdmError("audioPackFormat {apf.id} has type {apf.type.name}, but contains "
                               "audioChannelFormat {acf.id} with type {acf.type.name}".format(
                                   apf=audioPackFormat,
                                   acf=audioChannelFormat,
                               ))


def _validate_pack_subpack_types(adm):
    """Check that pack formats only contain pack formats of their specified type."""
    for audioPackFormat in adm.audioPackFormats:
        for sub_audioPackFormat in audioPackFormat.audioPackFormats:
            if sub_audioPackFormat.type != audioPackFormat.type:
                raise AdmError("audioPackFormat {apf.id} has type {apf.type.name}, but contains "
                               "audioPackFormat {sub_apf.id} with type {sub_apf.type.name}".format(
                                   apf=audioPackFormat,
                                   sub_apf=sub_audioPackFormat,
                               ))


def _validate_hoa_channels(adm):
    """Check that HOA audioChannelFormats only contain a single block format"""
    for audioChannelFormat in adm.audioChannelFormats:
        if audioChannelFormat.type == TypeDefinition.HOA:
            if len(audioChannelFormat.audioBlockFormats) != 1:
                # XXX: is this an ADM error, or an implementation limitation?
                raise AdmError("HOA audioChannelFormats must have exactly one block format, but {acf.id} has {n}".format(
                    acf=audioChannelFormat,
                    n=len(audioChannelFormat.audioBlockFormats),
                ))

            frequency = audioChannelFormat.frequency
            if frequency.lowPass is not None or frequency.highPass is not None:
                raise AdmError("HOA audioChannelFormats must not have frequency information, but {acf.id} does".format(
                    acf=audioChannelFormat,
                ))


def _validate_objects_channels(adm):
    """Check that Objects audioChannelFormats don't contain frequency
    information and have matching 'cartesian' and position attributes.
    """
    for audioChannelFormat in adm.audioChannelFormats:
        if audioChannelFormat.type == TypeDefinition.Objects:
            frequency = audioChannelFormat.frequency
            if frequency.lowPass is not None or frequency.highPass is not None:
                raise AdmError("Objects audioChannelFormats must not have frequency information, but {acf.id} does".format(
                    acf=audioChannelFormat,
                ))

            for audioBlockFormat in audioChannelFormat.audioBlockFormats:
                if audioBlockFormat.cartesian != isinstance(audioBlockFormat.position,
                                                            ObjectCartesianPosition):
                    raise AdmError("mismatch between cartesian element and coordinate type used in {abf.id}".format(
                        abf=audioBlockFormat,
                    ))


def _pack_format_paths_channels(audioPackFormat):
    for audioPackFormat_path in pack_format_paths_from(audioPackFormat):
        for audioChannelFormat in audioPackFormat_path[-1].audioChannelFormats:
            yield audioPackFormat_path, audioChannelFormat


def _hoa_pack_format_paths_channels(adm):
    for audioPackFormat in adm.audioPackFormats:
        if audioPackFormat.type == TypeDefinition.HOA:
            yield list(_pack_format_paths_channels(audioPackFormat))


def _validate_hoa_parameters_consistent(adm):
    from .hoa import (get_single_param, get_nfcRefDist, get_screenRef,
                      get_normalization, get_rtime, get_duration)

    for pack_paths_channels in _hoa_pack_format_paths_channels(adm):
        get_single_param(pack_paths_channels, "rtime", get_rtime)
        get_single_param(pack_paths_channels, "duration", get_duration)
        get_single_param(pack_paths_channels, "normalization", get_normalization)
        get_single_param(pack_paths_channels, "nfcRefDist", get_nfcRefDist)
        get_single_param(pack_paths_channels, "screenRef", get_screenRef)


def _validate_hoa_order_degree(adm):
    for audioPackFormat in adm.audioPackFormats:
        if audioPackFormat.type == TypeDefinition.HOA:

            orders_degrees = set()
            for audioChannelFormat in pack_format_channels(audioPackFormat):
                [audioBlockFormat] = audioChannelFormat.audioBlockFormats

                if audioBlockFormat.equation is not None:
                    raise AdmError("HOA audioBlockFormat {abf.id} has an 'equation' attribute, "
                                   "which overrides the 'order' and 'degree' attributes but "
                                   "has no defined format.".format(abf=audioBlockFormat))
                if audioBlockFormat.order is None:
                    raise AdmError("HOA audioBlockFormat {abf.id} has no 'order' attribute".format(abf=audioBlockFormat))
                if audioBlockFormat.degree is None:
                    raise AdmError("HOA audioBlockFormat {abf.id} has no 'degree' attribute".format(abf=audioBlockFormat))

                order_degree = (audioBlockFormat.order, audioBlockFormat.degree)

                if order_degree in orders_degrees:
                    raise AdmError("duplicate orders and degrees found in HOA audioPackFormat {apf.id}".format(apf=audioPackFormat))

                orders_degrees.add(order_degree)


def _validate_matrix_apf_references(apf):
    """Validate various aspects of the references starting at apf."""
    if apf.inputPackFormat is None and apf.outputPackFormat is None:
        raise AdmError("matrix audioPackFormat {apf.id} must have an input or output audioPackFormat reference".format(
            apf=apf,
        ))

    pack_type = matrix.type_of(apf)

    if (apf.inputPackFormat is not None and
            apf.inputPackFormat.type == TypeDefinition.Matrix):
        raise AdmError("audioPackFormat inputPackFormat reference in {apf.id} must not be of Matrix type".format(
            apf=apf,
        ))

    if (apf.outputPackFormat is not None and
            apf.outputPackFormat.type == TypeDefinition.Matrix):
        raise AdmError("audioPackFormat outputPackFormat reference in {apf.id} must not be of Matrix type".format(
            apf=apf,
        ))

    if pack_type != matrix.Type.DECODE and apf.encodePackFormats:
        raise AdmError("audioPackFormat {apf.id} has encode pack formats but is not a decode matrix".format(
            apf=apf,
        ))

    if pack_type == matrix.Type.DECODE and len(apf.encodePackFormats) != 1:
        raise AdmError("decode matrix audioPackFormats must have 1 encode matrix reference, "
                       "but {apf.id} has {n}".format(
                           apf=apf,
                           n=len(apf.encodePackFormats),
                       ))

    for apf_encode in apf.encodePackFormats:
        if apf_encode.type != TypeDefinition.Matrix:
            raise AdmError("audioPackFormat {apf.id} references non-Matrix type audioPackFormat "
                           "{apf_encode.id} as an encode matrix".format(
                               apf=apf, apf_encode=apf_encode,
                           ))

        if matrix.type_of(apf_encode) != matrix.Type.ENCODE:
            raise AdmError("audioPackFormat {apf.id} references non-encode type audioPackFormat "
                           "{apf_encode.id} as an encode matrix".format(
                               apf=apf, apf_encode=apf_encode,
                           ))

    if apf.audioPackFormats:
        raise AdmError("matrix audioPackFormat {apf.id} has audioPackFormat references".format(
            apf=apf,
        ))


def _validate_matrix_inputChannelFormat_references(matrix_pack):
    """Check that the inputChannelFormat references in matrix_pack reference
    channels of its input audioPackFormat"""
    input_pack = matrix.input_pack_format(matrix_pack)
    input_channels = list(pack_format_channels(input_pack))

    for matrix_channel in pack_format_channels(matrix_pack):
        [block_format] = matrix_channel.audioBlockFormats
        for matrix_element in block_format.matrix:
            input_channel = matrix_element.inputChannelFormat
            if not in_by_id(input_channel, input_channels):
                raise AdmError("matrix in audioChannelFormat {matrix_channel.id} references "
                               "input audioChannelFormat {input_channel.id} which is not in "
                               "the input or encode audioPackFormat {input_pack.id}".format(
                                   matrix_channel=matrix_channel,
                                   input_channel=input_channel,
                                   input_pack=input_pack,
                               ))


def _validate_matrix_outputChannelFormat_references(matrix_pack):
    """Check that the outputChannelFormat references form a 1-1 relationship
    between the channels of matrix_pack and the channels of its
    outputPackFormat"""
    output_pack_channels = list(pack_format_channels(matrix_pack.outputPackFormat))

    output_channels = []
    for matrix_channel in pack_format_channels(matrix_pack):
        [block_format] = matrix_channel.audioBlockFormats
        output_channel = block_format.outputChannelFormat
        if output_channel is None:
            raise AdmError("outputChannelFormat reference is missing in direct or "
                           "decode matrix block format {block_format.id}".format(
                               block_format=block_format,
                           ))

        if in_by_id(output_channel, output_channels):
            raise AdmError("duplicate outputChannelFormat reference to {output_channel.id} "
                           "in matrix audioPackFormat {matrix_pack.id}".format(
                               output_channel=output_channel,
                               matrix_pack=matrix_pack,
                           ))

        if not in_by_id(output_channel, output_pack_channels):
            raise AdmError("matrix audioChannelFormat {matrix_channel.id} references "
                           "audioChannelFormat {output_channel.id} which is not in the "
                           "output audioPackFormat of {matrix_pack.id}".format(
                               matrix_channel=matrix_channel,
                               output_channel=output_channel,
                               matrix_pack=matrix_pack,
                           ))

        output_channels.append(output_channel)

    for output_pack_channel in output_pack_channels:
        if not in_by_id(output_pack_channel, output_channels):
            raise AdmError("matrix audioPackFormat {matrix_pack.id} does not reference audioChannelFormat "
                           "{output_pack_channel.id} of output audioPackFormat".format(
                               matrix_pack=matrix_pack,
                               output_pack_channel=output_pack_channel,
                           ))


def _validate_non_matrix_pack(apf):
    """Check that matrix pack elements are not used in apf"""
    if apf.inputPackFormat is not None:
        raise AdmError("non-matrix audioPackFormat {apf.id} has inputPackFormat reference".format(apf=apf))
    if apf.outputPackFormat is not None:
        raise AdmError("non-matrix audioPackFormat {apf.id} has outputPackFormat reference".format(apf=apf))
    if apf.encodePackFormats:
        raise AdmError("non-matrix audioPackFormat {apf.id} has encodePackFormat references".format(apf=apf))


def _validate_matrix_channel(acf):
    """Check that acf has a single audioBlockFormat with appropriate parameters"""
    if len(acf.audioBlockFormats) != 1:
        raise AdmError("matrix audioChannelFormat {acf.id} does not have a single audioBlockFormat".format(
            acf=acf,
        ))

    [block_format] = acf.audioBlockFormats

    if block_format.rtime is not None or block_format.duration is not None:
        raise AdmError("matrix audioBlockFormat {block_format.id} has rtime or duration attributes".format(
            block_format=block_format,
        ))

    for coeff in block_format.matrix:
        for name in "gainVar", "delayVar", "phaseVar", "phase":
            value = getattr(coeff, name)
            if value is not None:
                raise AdmError("{name} attribute used in {block_format.id} is not supported".format(
                    name=name,
                    block_format=block_format,
                ))

        if coeff.delay is not None and coeff.delay < 0:
            raise AdmError("delay attribute used in {block_format.id} must be non-negative".format(
                block_format=block_format,
            ))


def _validate_matrix_types(adm):
    """Complete validation of matrix format information"""
    for acf in adm.audioChannelFormats:
        if acf.type == TypeDefinition.Matrix:
            _validate_matrix_channel(acf)

    for apf in adm.audioPackFormats:
        if apf.type == TypeDefinition.Matrix:
            _validate_matrix_apf_references(apf)
            _validate_matrix_inputChannelFormat_references(apf)
            if matrix.type_of(apf) in (matrix.Type.DECODE, matrix.Type.DIRECT):
                _validate_matrix_outputChannelFormat_references(apf)
        else:
            _validate_non_matrix_pack(apf)


def validate_structure(adm):
    adm.validate()
    _validate_object_loops(adm)
    _validate_pack_channel_types(adm)
    _validate_pack_subpack_types(adm)
    _validate_pack_channel_multitree(adm)
    _validate_objects_channels(adm)
    _validate_hoa_channels(adm)
    _validate_hoa_order_degree(adm)
    _validate_hoa_parameters_consistent(adm)
    _validate_matrix_types(adm)


def validate_selected_audioTrackUID(audioTrackUID):
    """Check that an audioTrackUID has references required for this implementation"""
    if audioTrackUID.trackIndex is None:
        raise AdmError("audioTrackUID {atu.id} does not have a track index, "
                       "which should be specified in the CHNA chunk".format(
                           atu=audioTrackUID,
                       ))

    if audioTrackUID.audioTrackFormat is None:
        raise AdmError("audioTrackUID {self.id} is not linked "
                       "to an audioTrackFormat".format(
                           self=audioTrackUID,
                       ))

    if audioTrackUID.audioPackFormat is None:
        raise AdmError("audioTrackUID {atu.id} does not have an audioPackFormat "
                       "reference. This may be used in coded formats, which are not "
                       "currently supported.".format(
                           atu=audioTrackUID,
                       ))

    audioStreamFormat = audioTrackUID.audioTrackFormat.audioStreamFormat

    if audioStreamFormat.audioChannelFormat is None:
        raise AdmError("audioStreamFormat {asf.id} does not have an audioChannelFormat "
                       "reference. This may be used in coded formats, which are not "
                       "currently supported.".format(
                           asf=audioStreamFormat,
                       ))


def possible_audioTrackUID_errors(audioTrackUID):
    audioPackFormat = audioTrackUID.audioPackFormat

    track_channel = (audioTrackUID
                     .audioTrackFormat
                     .audioStreamFormat
                     .audioChannelFormat)

    possible_packs = [audioPackFormat] + audioPackFormat.encodePackFormats
    if audioPackFormat.inputPackFormat is not None:
        possible_packs.append(audioPackFormat)

    if not any(pack_channel is track_channel
               for possible_pack in possible_packs
               for pack_channel in pack_format_channels(possible_pack)):
        yield ("audioPackFormat {apf.id} does not reference "
               "audioChannelFormat {acf.id} which is referenced "
               "by audioTrackUID {atu.id} via audioTrackFormat and audioStreamFormat".format(
                   apf=audioPackFormat,
                   acf=track_channel,
                   atu=audioTrackUID,
               ))


def possible_audioTrackUID_pack_errors(selected_packs, selected_tracks):
    possible_packs = []
    for pack in selected_packs:
        possible_packs.extend(pack_format_packs(pack))
        for encode_pack in pack.encodePackFormats:
            possible_packs.extend(pack_format_packs(encode_pack))

    for track in selected_tracks:
        if not in_by_id(track.audioPackFormat, possible_packs):
            yield ("audioPackFormat {apf.id} referenced from audioTrackUID {atu.id} "
                   "is not referenced from audioObject".format(
                       apf=track.audioPackFormat,
                       atu=track,
                   ))


def possible_reference_errors(selected_packs, selected_tracks, num_silent_tracks):
    if selected_packs is not None:
        if len(selected_packs) > 1:
            yield "reference to more than one audioPackFormat"

        if (selected_tracks or num_silent_tracks) and not selected_packs:
            yield "references to audioTrackUIDs but not to audioPackFormats"

        if not (selected_tracks or num_silent_tracks) and selected_packs:
            yield "references to audioPackFormats but not to audioTrackUIDs"

        for error in possible_audioTrackUID_pack_errors(selected_packs, selected_tracks):
            yield error

    for track in selected_tracks:
        for error in possible_audioTrackUID_errors(track):
            yield error
