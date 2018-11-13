from itertools import chain
import warnings
from collections import OrderedDict
from six import iteritems
from .exceptions import AdmIDError, AdmIDWarning


class ADM(object):

    def __init__(self):
        self._ap = []
        self._ac = []
        self._ao = []
        self._apf = []
        self._acf = []
        self._asf = []
        self._atf = []
        self._atu = []

        self._object_lists = (
            self._ap,
            self._ac,
            self._ao,
            self._apf,
            self._acf,
            self._asf,
            self._atf,
            self._atu)

    @classmethod
    def _without_duplicates(cls, obj_list):
        """Remove objects with duplicate IDs.

        For each id, there should only be one object with that id. If there are
        two objects, and one is a common definition and one isn't, then a
        warning is issued and the non-common definition is used.
        """
        by_id = OrderedDict()

        for obj in obj_list:
            if obj.id is None:
                yield obj
            else:
                by_id.setdefault(obj.id.upper(), []).append(obj)

        for id, objects in iteritems(by_id):
            common = [obj for obj in objects if obj.is_common_definition]
            non_common = [obj for obj in objects if not obj.is_common_definition]

            # check for errors
            assert len(common) <= 1, "duplicate common definitions found"
            if len(non_common) > 1:
                raise AdmIDError("duplicate objects with id={id}".format(id=id))
            assert common or non_common

            if non_common:
                if common:
                    warnings.warn("non-common-definition element found with id {id} that overrides a common-definition element".format(id=id),
                                  AdmIDWarning)
                yield non_common[0]
            else:
                yield common[0]

    def lazy_lookup_references(self):
        for obj_list in self._object_lists:
            obj_list[:] = self._without_duplicates(obj_list)

        for element in self.elements:
            element.lazy_lookup_references(self)

    def validate(self):
        for element in self.elements:
            element.validate()

    def addAudioProgramme(self, programme):
        self._ap.append(programme)

    def addAudioContent(self, content):
        self._ac.append(content)

    def addAudioObject(self, audioobject):
        self._ao.append(audioobject)

    def addAudioPackFormat(self, packformat):
        self._apf.append(packformat)

    def addAudioChannelFormat(self, channelformat):
        self._acf.append(channelformat)

    def addAudioStreamFormat(self, streamformat):
        self._asf.append(streamformat)

    def addAudioTrackFormat(self, trackformat):
        self._atf.append(trackformat)

    def addAudioTrackUID(self, trackUID):
        self._atu.append(trackUID)

    @property
    def elements(self):
        return chain(*self._object_lists)

    def __getitem__(self, key):
        return self.lookup_element(key)

    def lookup_element(self, key):
        key_upper = key.upper()
        for element in self.elements:
            if element.id is not None and element.id.upper() == key_upper:
                return element
        raise KeyError('Unknown element requested {0}'.format(key))

    @property
    def audioProgrammes(self):
        return self._ap

    @property
    def audioContents(self):
        return self._ac

    @property
    def audioObjects(self):
        return self._ao

    @property
    def audioPackFormats(self):
        return self._apf

    @property
    def audioChannelFormats(self):
        return self._acf

    @property
    def audioStreamFormats(self):
        return self._asf

    @property
    def audioTrackFormats(self):
        return self._atf

    @property
    def audioTrackUIDs(self):
        return self._atu
