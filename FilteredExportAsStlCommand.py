import adsk.core
import adsk.fusion
import traceback
import os.path
import re

from .FilteredExportUtil import renderResultMessage
from .FilteredExportUtil import FilteredExportResult

from .Fusion360Utilities.Fusion360Utilities import AppObjects
from .Fusion360Utilities.Fusion360CommandBase import Fusion360CommandBase

# Faked statics for easy code maintainance
S_STL_REFINEMENT_LOOKUP = 'stlDropDownStlRefinement'
S_STL_REFINEMENT_LOW = 'Low'
S_STL_REFINEMENT_MEDIUM = 'Medium'
S_STL_REFINEMENT_HIGH = 'High'
S_STL_REFINEMENT_ULTRA = 'Ultra'
S_STL_REFINEMENT_CUSTOM = 'Custom'
S_STL_SURFACE_DEVIATION = 'stlSurfaceDeviation'
S_STL_NORMAL_DEVIATION = 'stlNormalDeviation'
S_STL_MAXIMUM_EDGE_LENGTH = 'stlMaximumEdgeLength'
S_STL_ASPECT_RATIO = 'stlAspectRatio'
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
S_STL_EXPORT_COMPONENT_NAME_TYPE = 'stlDropDownExportComponentNameType'
S_STL_EXPORT_COMPONENT_NAME_TYPE_LAST_FROM_PATH = 'Last From Path'
S_STL_EXPORT_COMPONENT_NAME_TYPE_FULL_PATH = 'Full Path'
S_STL_EXPORT_ADD_REFINMENT_NAME_TO_NAME = 'stlExportAddRefinmentNameToName'

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
        #remove versions from root
        result = re.sub(r' v[0-9]*$', '', result)
        
    result = re.sub(r':', '__', result)

    if removeSpaces:
        # remove leading and tailing spaces
        result = result.strip()

        # replace spaces with underscores (_)
        result = result.replace(' ', '_')
    
    # if the name contains dots it will fail silently during the export. 
    # Replace it with a double underscore. 
    result = result.replace('.', '__')

    return result


#
# cleans up a component path by removing leading and tailing spaces, version tags and
# replaces blanks with underscores (_)
#
def getCleanNameFromComponentPath(name, removeVersionTagFromNames, removeSpaces):
    result = name

    # remove versions from components from path
    if removeVersionTagFromNames:
        result = re.sub(r':[0-9]*\+', '-', result)
        result = re.sub(r':[0-9]*$', '', result)
    else:
        result = re.sub(r'\+', '__', result)
        result = re.sub(r':', '__', result)
    
    return getCleanName(result, removeVersionTagFromNames, removeSpaces)
    
    
#
# Get file name from body's name and component's name and remove unwanted information
#
def getFileName(body, rootComponent, addRootComponentNameToFilename, \
                    addComponentNameToFilename, addLastComponentNameOnly, \
                    removeVersionTagFromNames, removeSpaces, addRefinmentName, \
                    refinementName, fileNames):

    # build temporary  file name
    tmpFileName = ''

    if addRefinmentName:
        tmpFileName += refinementName + '-'
        
    # add root component name if checked
    if addRootComponentNameToFilename and (rootComponent != body[0].parentComponent or not addComponentNameToFilename):
        tmpFileName += getCleanName(rootComponent.name, removeVersionTagFromNames, removeSpaces) + '-'

    # add component name if checked and is differnt to root component
    if addComponentNameToFilename:
        if addLastComponentNameOnly: 
            tmpFileName += getCleanName(body[0].parentComponent.name, removeVersionTagFromNames, removeSpaces) + '-'
        else:
            tmpFileName += getCleanNameFromComponentPath(body[1], removeVersionTagFromNames, removeSpaces) + '-'

    tmpFileName += getCleanName(body[0].name, removeVersionTagFromNames, removeSpaces)
    
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
def exportStls(bodies: list, rootComponent, input_values, appObjects):
    # list of processed file names
    processedFiles = []

    # get export path
    exportPath = getPath(appObjects)

    # export stl as binary (True) or text (False)
    exportAsBinary = input_values[S_STL_FORMAT_LOOKUP] == S_STL_FORMAT_BINARY

    # if file name is empty, replace it with a know directory
    if exportPath == '':
        exportPath = os.path.dirname

    # export each body as stl
    for body in bodies:
        # get clean file name
    
        fileName = getFileName(body, rootComponent, \
                                    input_values[S_STL_EXPORT_ADD_ROOT_NAME_TO_FILENAME_LOOKUP], \
                                    input_values[S_STL_EXPORT_ADD_COMPONENT_NAME_TO_FILENAME_LOOKUP], \
                                    input_values[S_STL_EXPORT_COMPONENT_NAME_TYPE] == S_STL_EXPORT_COMPONENT_NAME_TYPE_LAST_FROM_PATH, \
                                    input_values[S_STL_EXPORT_REMOVE_VERSION_FROM_FILENAME_LOOKUP], \
                                    input_values[S_STL_EXPORT_REMOVE_SPACES_FROM_FILENAME_LOOKUP], \
                                    input_values[S_STL_EXPORT_ADD_REFINMENT_NAME_TO_NAME], \
                                    input_values[S_STL_REFINEMENT_LOOKUP], \
                                    processedFiles)
        
        # create full export name (including path)
        fullFileName = os.path.join(exportPath, fileName)

        # create common export options
        stlExportOptions = appObjects.export_manager.createSTLExportOptions(body[0], fullFileName)
        stlExportOptions.setToPrintUtility = False
        stlExportOptions.isBinaryFormat = exportAsBinary
        
        # adjust for ultra settings
        if input_values[S_STL_REFINEMENT_LOOKUP] == S_STL_REFINEMENT_ULTRA:
            stlExportOptions.meshRefinement = 3
            stlExportOptions.surfaceDeviation = input_values[S_STL_SURFACE_DEVIATION]
            stlExportOptions.normalDeviation = input_values[S_STL_NORMAL_DEVIATION]
        
        elif input_values[S_STL_REFINEMENT_LOOKUP] == S_STL_REFINEMENT_HIGH:
            stlExportOptions.meshRefinement = 0
        
        elif input_values[S_STL_REFINEMENT_LOOKUP] == S_STL_REFINEMENT_MEDIUM:
            stlExportOptions.meshRefinement = 1
        
        elif input_values[S_STL_REFINEMENT_LOOKUP] == S_STL_REFINEMENT_LOW:
            stlExportOptions.meshRefinement = 2
        
        elif input_values[S_STL_REFINEMENT_LOOKUP] == S_STL_REFINEMENT_CUSTOM:
            stlExportOptions.mesRefinement = 3
            stlExportOptions.surfaceDeviation = input_values[S_STL_SURFACE_DEVIATION]
            stlExportOptions.normalDeviation = input_values[S_STL_NORMAL_DEVIATION]

        # create stl file
        appObjects.export_manager.execute(stlExportOptions)

        # add file name to processed list
        processedFiles.append(fileName)

    return FilteredExportResult(exportPath, processedFiles, '')


#
# get a list of all bodies from all components
#
def getBodies(components: list, bodies: list):
    # iterate over components
    for component in components:
        # process all bodies from the current component
        if len(component) > 0:
            for body in component[0].bRepBodies:
                # add to list, if the body is not hidden
                if body.isLightBulbOn:
                    bodies.append([body, component[1]])

    if len(bodies) <= 0:
        raise ValueError('No bodies found.')

    return bodies


#
# get all child occurences (components) recursively from a component
# and return a unique list of components
#
def getComponents(occurences, components: list, includeSubComponents, filterLinkedComponents):
    # iterate over all occurences
    for occurence in occurences:
        if (filterLinkedComponents == True and occurence.isReferencedComponent == False) or filterLinkedComponents == False:        
            # if the component is not hidden process the component
            if occurence.isLightBulbOn:
                # validate if the current component was already processed
                componentFound = False
                component = adsk.fusion.Component.cast(None)
    
                # itereate over unique component list and compoare current
                # occource with element of unique component list
                for component in components:
                    if component[0] == occurence.component:
                        # component exisits in filted list. No need to process
                        # the full list
                        componentFound = True
                        break
    
                # if occurence not found in unique list of components, add this
                # occurence because it's new
                if not componentFound and occurence.component:
                    components.append([occurence.component, occurence.fullPathName])
    
                # if this occurence has sub components process them, too
                if occurence.childOccurrences and not componentFound and includeSubComponents:
                    components = getComponents(occurence.childOccurrences, components, includeSubComponents, filterLinkedComponents)


    return components

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
                components.append([rootComponent, rootComponent.name])
                
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

        # Refinement (High, Medium, Low)
        dropDownStlRefinement = inputs.addDropDownCommandInput(S_STL_REFINEMENT_LOOKUP, 'Refinement', adsk.core.DropDownStyles.LabeledIconDropDownStyle);
        dropDownStlRefinementItems = dropDownStlRefinement.listItems
        dropDownStlRefinementItems.add(S_STL_REFINEMENT_ULTRA, False, '')
        dropDownStlRefinementItems.add(S_STL_REFINEMENT_HIGH, True, '')
        dropDownStlRefinementItems.add(S_STL_REFINEMENT_MEDIUM, False, '')
        dropDownStlRefinementItems.add(S_STL_REFINEMENT_LOW, False, '')
        dropDownStlRefinementItems.add(S_STL_REFINEMENT_CUSTOM, False, '')
        
        inputs.addFloatSpinnerCommandInput(S_STL_SURFACE_DEVIATION, 'Surface deviation', 'mm', 0.000846, 0.084635, .01, 0.001016).isEnabled = False
        inputs.addFloatSpinnerCommandInput(S_STL_NORMAL_DEVIATION, 'Normal deviation', '', 1.0000, 41, 1, 10.0000).isEnabled = False

        # Filter linked components
        inputs.addBoolValueInput(S_STL_FILTER_LINKED_COMPONENTS, 'Filter linked components', True, '', False).value = False

        # Define filename options
        groupFileNameOptions = inputs.addGroupCommandInput(S_STL_GROUP_FILENAME_OPTIONS_LOOKUP, 'Filename Options')
        groupFileNameOptions.isExpanded = True
        groupFileNameOptionsChildInput = groupFileNameOptions.children

        # True if the refinement name should be added to the filename otherwise false
        groupFileNameOptionsChildInput.addBoolValueInput(S_STL_EXPORT_ADD_REFINMENT_NAME_TO_NAME, 'Add refinement name', True).value = False

        # True if the name of the root component should be added to the file name otherwise false
        groupFileNameOptionsChildInput.addBoolValueInput(S_STL_EXPORT_ADD_ROOT_NAME_TO_FILENAME_LOOKUP, 'Add root name', True).value = True

        # True if the component name should be added to the file name otherwise false
        groupFileNameOptionsChildInput.addBoolValueInput(S_STL_EXPORT_ADD_COMPONENT_NAME_TO_FILENAME_LOOKUP, 'Add component name', True).value = True
        
        dropDownComponentNameType = groupFileNameOptionsChildInput.addDropDownCommandInput(S_STL_EXPORT_COMPONENT_NAME_TYPE, 'Component name type', adsk.core.DropDownStyles.LabeledIconDropDownStyle);
        dropDownComponentNameTypeItems = dropDownComponentNameType.listItems
        dropDownComponentNameTypeItems.add(S_STL_EXPORT_COMPONENT_NAME_TYPE_LAST_FROM_PATH, True, '')
        dropDownComponentNameTypeItems.add(S_STL_EXPORT_COMPONENT_NAME_TYPE_FULL_PATH, False, '')

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

        # Add component names to filenames?
        if changed_input.id == S_STL_EXPORT_ADD_COMPONENT_NAME_TO_FILENAME_LOOKUP:
            if changed_input.value == True:
                # show component name style if 'add components to name' is true otherwise hide the drop down list.
                inputs.itemById(S_STL_EXPORT_COMPONENT_NAME_TYPE).isVisible = True
            else:
                # hide component name style if 'add components to name' is true otherwise hide the drop down list.
                inputs.itemById(S_STL_EXPORT_COMPONENT_NAME_TYPE).isVisible = False

        elif changed_input.id == S_STL_REFINEMENT_LOOKUP:
            if input_values[S_STL_REFINEMENT_LOOKUP] == S_STL_REFINEMENT_ULTRA:
                inputs.itemById(S_STL_SURFACE_DEVIATION).value = 0.000508
                inputs.itemById(S_STL_NORMAL_DEVIATION).value = 5.0000
                inputs.itemById(S_STL_SURFACE_DEVIATION).isEnabled = False
                inputs.itemById(S_STL_NORMAL_DEVIATION).isEnabled = False

            elif input_values[S_STL_REFINEMENT_LOOKUP] == S_STL_REFINEMENT_HIGH:
                inputs.itemById(S_STL_SURFACE_DEVIATION).value = 0.001016
                inputs.itemById(S_STL_NORMAL_DEVIATION).value = 10.0000
                inputs.itemById(S_STL_SURFACE_DEVIATION).isEnabled = False
                inputs.itemById(S_STL_NORMAL_DEVIATION).isEnabled = False
                
            elif input_values[S_STL_REFINEMENT_LOOKUP] == S_STL_REFINEMENT_MEDIUM:
                inputs.itemById(S_STL_SURFACE_DEVIATION).value = 0.003212
                inputs.itemById(S_STL_NORMAL_DEVIATION).value = 15.0000
                inputs.itemById(S_STL_SURFACE_DEVIATION).isEnabled = False
                inputs.itemById(S_STL_NORMAL_DEVIATION).isEnabled = False
                
            elif input_values[S_STL_REFINEMENT_LOOKUP] == S_STL_REFINEMENT_LOW:
                inputs.itemById(S_STL_SURFACE_DEVIATION).value = 0.008069
                inputs.itemById(S_STL_NORMAL_DEVIATION).value = 30.0000
                inputs.itemById(S_STL_SURFACE_DEVIATION).isEnabled = False
                inputs.itemById(S_STL_NORMAL_DEVIATION).isEnabled = False
                
            elif input_values[S_STL_REFINEMENT_LOOKUP] == S_STL_REFINEMENT_CUSTOM:
                inputs.itemById(S_STL_SURFACE_DEVIATION).isEnabled = True
                inputs.itemById(S_STL_NORMAL_DEVIATION).isEnabled = True                