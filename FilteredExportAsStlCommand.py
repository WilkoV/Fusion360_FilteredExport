import adsk.core
import adsk.fusion
import traceback
import os.path
import re

from .FilteredExportUtil import getComponents
from .FilteredExportUtil import renderResultMessage
from .FilteredExportUtil import FilteredExportResult

from .Fusion360Utilities.Fusion360Utilities import AppObjects
from .Fusion360Utilities.Fusion360CommandBase import Fusion360CommandBase

# Faked statics for easy code maintainance
S_STL_REFINEMENT_LOOKUP = 'stlDropDownStlRefinement'
S_STL_REFINEMENT_LOW = 'Low'
S_STL_REFINEMENT_MEDIUM = 'Medium'
S_STL_REFINEMENT_HIGH = 'High'
S_STL_FORMAT_LOOKUP = 'stlDropDownStlFormat'
S_STL_FORMAT_BINARY = 'Binary'
S_STL_FORMAT_TEXT = 'Text'
S_STL_EXPORT_ADD_ROOT_NAME_TO_FILENAME_LOOKUP = 'stlExportAddRootNameToFilename'
S_STL_EXPORT_ADD_COMPONENT_NAME_TO_FILENAME_LOOKUP = 'stlExportAddComponentNameToFilename'
S_STL_EXPORT_REMOVE_VERSION_FROM_FILENAME_LOOKUP = 'stlExportFileRemoveVersionTagFromNames'
S_STL_EXPORT_REMOVE_SPACES_FROM_FILENAME_LOOKUP = 'stlExportFileRemoveSpacesFromNames'
S_STL_GROUP_FILENAME_OPTIONS_LOOKUP = 'stlFilenameGroupFilenameOptions'
S_STL_SELECTION_LOOKUP='stlSelection'
S_STL_FILTER_LINKED_COMPONENTS = 'stlExportFilterLinkedComponents'

# build a file name from a component. File name looks like:
# body parent component name + - + body name. leading and
# tailing blanks will be removed and blanks are replace replaced
# with an underscore.
# If the file name already exists in a list, and index suffix will
# be added (index)
#


#
# cleans up a name by removing leading and tailing spaces, version tags and
# replaces blanks with underscores (_)
#
def getCleanName(name, removeVersionTagFromNames, removeSpaces):
    result = name

    # remove version tag
    if removeVersionTagFromNames:
        result = re.sub(r' v[0-9]*$', '', result)
        
    result.replace(':', '__')

    if removeSpaces:
        # remove leading and tailing spaces
        result = result.strip()

        # replace spaces with underscores (_)
        result = result.replace(' ', '_')
    
    # if the name contains dots it will fail silently during the export. 
    # Replace it with a double underscore. 
    result = result.replace('.', '__')

    return result

def getFileName(body, rootComponent, addRootComponentNameToFilename, \
                    addComponentNameToFilename, removeVersionTagFromNames, \
                    removeSpaces, fileNames):

    # get clean names
    rootName = getCleanName(rootComponent.name, removeVersionTagFromNames, removeSpaces)
    componentName = getCleanName(body.parentComponent.name, removeVersionTagFromNames, removeSpaces)
    bodyName = getCleanName(body.name, removeVersionTagFromNames, removeSpaces)

    # build temporary  file name
    tmpFileName = ''

    # add root component name if checked
    if addRootComponentNameToFilename and (rootComponent != body.parentComponent or not addComponentNameToFilename):
        tmpFileName += rootName + '-'

    # add component name if checked and is differnt to root component
    if addComponentNameToFilename :
        tmpFileName += componentName + '-'

    tmpFileName += bodyName

    # make file name unique within this export
    fileName = tmpFileName
    suffix = 1

    while fileName in fileNames:
        fileName = tmpFileName + '_(' + str(suffix) + ')'
        suffix += 1

    # return unique file name
    return fileName

#
# get path via dialog
#
def getPath(appObjects):
    # return value
    exportPath = ''

    # create dialog
    folderDialog = appObjects.ui.createFolderDialog()
    folderDialog.title = 'Export Folder'

    # open dialog
    dialogResult = folderDialog.showDialog()

    # check if user finished the dialog by pressing okay
    if dialogResult == adsk.core.DialogResults.DialogOK:
        exportPath = str.format(folderDialog.folder)
    else:
        # user canceled the dialog
        raise ValueError('No export path defined.')

    # return formated path
    return exportPath

#
# export the list of bodies as STL files
#
def exportStls(bodies, rootComponent, input_values, appObjects):
    # list of processed file names
    processedFiles = []

    # get export path
    exportPath = getPath(appObjects)

    # export stl as binary (True) or text (False)
    exportAsBinary = input_values[S_STL_FORMAT_LOOKUP] == S_STL_FORMAT_BINARY

    # export refinment (low, medium, high)
    exportRefinement = 'MeshRefinementHigh'

    if input_values[S_STL_REFINEMENT_LOOKUP] == S_STL_REFINEMENT_LOW:
        exportRefinement = 'MeshRefinementLow'
    elif input_values[S_STL_REFINEMENT_LOOKUP] == S_STL_REFINEMENT_MEDIUM:
        exportRefinement = 'MeshRefinementMedium'

    # if file name is empty, replace it with a know directory
    if exportPath == '':
        exportPath = os.path.dirname


    # export each body as stl
    for body in bodies:
        # get clean file name
        fileName = getFileName(body, rootComponent, \
                                    input_values[S_STL_EXPORT_ADD_ROOT_NAME_TO_FILENAME_LOOKUP], \
                                    input_values[S_STL_EXPORT_ADD_COMPONENT_NAME_TO_FILENAME_LOOKUP], \
                                    input_values[S_STL_EXPORT_REMOVE_VERSION_FROM_FILENAME_LOOKUP], \
                                    input_values[S_STL_EXPORT_REMOVE_SPACES_FROM_FILENAME_LOOKUP], \
                                    processedFiles)

        # create full export name (including path)
        fullFileName = os.path.join(exportPath, fileName)

        # create export options
        stlExportOptions = appObjects.export_manager.createSTLExportOptions(body, fullFileName)
        stlExportOptions.setToPrintUtility = False
        stlExportOptions.isBinaryFormat = exportAsBinary
        stlExportOptions.mesRefinement = exportRefinement

        # create stl file
        appObjects.export_manager.execute(stlExportOptions)

        # add file name to processed list
        processedFiles.append(fileName)

    return FilteredExportResult(exportPath, processedFiles, '')


#
# get a list of all bodies from all components
#
def getBodies(components, bodies):
    # iterate over components
    for component in components:
        # process all bodies from the current component
        for body in component.bRepBodies:
            # add to list, if the body is not hidden
            if body.isLightBulbOn:
                bodies.append(body)

    if len(bodies) <= 0:
        raise ValueError('No bodies found.')

    return bodies


#
# Export all boides within a design as separate STL file. The logic ensures
# the components are not exported
#
class FilteredExportAsStlCommand(Fusion360CommandBase):
    # Run when the user presses OK
    def on_execute(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs, args, input_values):
        try:
            appObjects = AppObjects()

            # no design? Nothing to do
            if not appObjects.design:
                raise ValueError('No active Fusion design', 'No Design')

            # get root component
            rootComponent = appObjects.design.rootComponent

            # get component list (recursive)
            components = []

            # selection available?
            if S_STL_SELECTION_LOOKUP in input_values:
                if input_values[S_STL_SELECTION_LOOKUP][0] == rootComponent:
                    components = getComponents(rootComponent.occurrences, components, True, input_values[S_STL_FILTER_LINKED_COMPONENTS])
                else:
                    # process selcted components
                    components = getComponents(input_values[S_STL_SELECTION_LOOKUP], components, True, input_values[S_STL_FILTER_LINKED_COMPONENTS])
            else:
                # process all components
                components = getComponents(rootComponent.occurrences, components, True, input_values[S_STL_FILTER_LINKED_COMPONENTS])
                # add root component to list, because it can contain bodies, too
                components.append(rootComponent)

            # get all bodies
            bodies = []
            bodies = getBodies(components, bodies)

            # process bodies
            exportResult = exportStls(bodies, rootComponent, input_values, appObjects)

            # show result list
            appObjects.ui.messageBox(renderResultMessage(exportResult))

        except ValueError as e:
            if appObjects.ui:
                appObjects.ui.messageBox(str(e))
        except:
            if appObjects.ui:
                appObjects.ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


    # Run when the user selects your command icon from the Fusion 360 UI
    def on_create(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs):
        # Select objects to process
        selectionCommand = inputs.addSelectionInput(S_STL_SELECTION_LOOKUP, 'Select Components', '')
        selectionCommand.setSelectionLimits(0)
        selectionCommand.addSelectionFilter('Occurrences')


        # STL Format (Binary or Text)
        dropDownStlFormat = inputs.addDropDownCommandInput(S_STL_FORMAT_LOOKUP, 'Format', adsk.core.DropDownStyles.LabeledIconDropDownStyle);
        dropDownStlFormatItems = dropDownStlFormat.listItems
        dropDownStlFormatItems.add(S_STL_FORMAT_BINARY, True, '')
        dropDownStlFormatItems.add(S_STL_FORMAT_TEXT, False, '')

        # Filter linked components
        filterLinkedComponents = inputs.addBoolValueInput(S_STL_FILTER_LINKED_COMPONENTS, 'Filter linked components', True, '', False).value = False

        # Refinement (High, Medium, Low)
        dropDownStlRefinement = inputs.addDropDownCommandInput(S_STL_REFINEMENT_LOOKUP, 'Refinement', adsk.core.DropDownStyles.LabeledIconDropDownStyle);
        dropDownStlRefinementItems = dropDownStlRefinement.listItems
        dropDownStlRefinementItems.add(S_STL_REFINEMENT_HIGH, True, '')
        dropDownStlRefinementItems.add(S_STL_REFINEMENT_MEDIUM, False, '')
        dropDownStlRefinementItems.add(S_STL_REFINEMENT_LOW, False, '')

        # Define filename options
        groupFileNameOptions = inputs.addGroupCommandInput(S_STL_GROUP_FILENAME_OPTIONS_LOOKUP, 'Filename Options')
        groupFileNameOptions.isExpanded = False
        groupFileNameOptionsChildInput = groupFileNameOptions.children

        # True if the name of the root component should be added to the file name otherwise false
        groupFileNameOptionsChildInput.addBoolValueInput(S_STL_EXPORT_ADD_ROOT_NAME_TO_FILENAME_LOOKUP, 'Add root name', True).value = True

        # True if the component name should be added to the file name otherwise false
        groupFileNameOptionsChildInput.addBoolValueInput(S_STL_EXPORT_ADD_COMPONENT_NAME_TO_FILENAME_LOOKUP, 'Add component name', True).value = True

        # True if the verstion tag should be removed otherwise false
        groupFileNameOptionsChildInput.addBoolValueInput(S_STL_EXPORT_REMOVE_VERSION_FROM_FILENAME_LOOKUP, 'Remove version tags', True).value = True

        # True if spaces should be removed or replaced otherwise false
        groupFileNameOptionsChildInput.addBoolValueInput(S_STL_EXPORT_REMOVE_SPACES_FROM_FILENAME_LOOKUP, 'Remove spaces', True).value = True

    # Run whenever a user makes any change to a value or selection in the addin UI
    def on_preview(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs, args, input_values):
        pass


    # Run after the command is finished.
    def on_destroy(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs, reason, input_values):
        pass


    # Run when any input is changed.
    def on_input_changed(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs, changed_input, input_values):
        pass

