from datetime import datetime
import cPickle as pickle

from mongoengine.fields import EmbeddedDocumentField, ListField, StringField, DateTimeField, ReferenceField, BinaryField
from mongoengine.document import EmbeddedDocument, Document

from powerwall import KnownClass


class Note(EmbeddedDocument):
    """Stores some kind of record about a tool"""

    _note = StringField(required=True)
    """User-specified note"""

    author = StringField(required=True)
    """Author of this note"""

    created = DateTimeField(required=True)
    """When this note was created"""

    edited = DateTimeField(required=True)
    """When this note was edited last"""

    def __init__(self, *args, **kwargs):
        super(Note, self).__init__(*args, **kwargs)

        # Mark when this note was created
        self.created = datetime.now()
        self.edited = datetime.now()

        # Set the note value
        if 'note' in kwargs:
            self.note = kwargs['note']

    @property
    def note(self):
        """User-specified note"""
        return self._note

    @note.setter
    def note(self,value):
        """Sets the value of the note

        :param value: New value of note
        """

        # Update the value
        self._note = value
        # When this note was last edited
        self.edited = datetime.now()


class WorkflowTool(Document):
    """Abstract class that defines a workflow tool

    Stores name and description, any notes about the tool, and its dependencies. Provides a uniform interface to access
    these capabilities
    """

    meta = {'allow_inheritance': True}

    name = StringField(required=True, regex="^[^\\s+]*$")
    """Name of this tool. Cannot have whitespace"""

    description = StringField(required=True)
    """Description of this tool"""

    last_run = DateTimeField()
    """Last time this object was run"""

    notes = ListField(EmbeddedDocumentField(Note))
    """Any notes about this tool"""

    previous_step = ReferenceField('WorkflowTool')
    """Previous step / dependency for this tool.

    LW 11July2016: Consider making this a ListField to have multiple dependencies"""

    toolchain = ReferenceField('ToolChain', required=True)
    """Tool chain that this tool is associated with"""

    _result_cache = None
    """Holds a dictionary results from this calculation"""

    result = BinaryField()
    """Holds the pickled version of `result_cache`"""

    def __init__(self, *args, **kwargs):
        super(WorkflowTool, self).__init__(*args, **kwargs)

        # Register this class with the KnownClass library
        KnownClass.register_class(self)

    def get_input(self):
        """Get the results from the previous step, which are used as input into this transformer

        :return: Dict, results from the previous step. Dictionary at least contains an entry 'data' that matches the
        dataset from the previous step
        """

        if self.previous_step is None:
            # Get data from the host workflow
            data = self.toolchain.extractor.get_data()

            # Return the dictionary
            return {'data': data}

        # Get result from previous step
        return self.previous_step.run()

    def run(self):
        """Run an analysis tool

        If the tool has already been run, returns cached result

        Output:
            :return: dict, result from the analysis tool
        """

        if self._result_cache is None:
            if self.result is not None:
                self._result_cache = pickle.loads(self.result)
            else:
                # Get the inputs
                inputs = self.get_input()
                if 'data' not in inputs:
                    raise Exception('Input does not include data field')
                data = inputs['data']
                del inputs['data']

                # Run the transformer
                data, outputs = self._run(data, inputs)
                outputs['data'] = data
                self._result_cache = outputs
                self.last_run = datetime.now()

        # Print out the results
        return self._result_cache

    def _run(self, data, other_inputs):
        """Do the actual running

        :param data: DataFrame, data to be transformed
        :param other_inputs: dict, other inputs to the transformer
        :return: Dictionary holding results from this transformer
        """
        raise NotImplementedError()

    def save(self):
        # Pickle result cache, if present
        if self._result_cache is not None:
            self.result = pickle.dumps(self._result_cache)

        super(WorkflowTool, self).save()