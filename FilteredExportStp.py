import adsk.core
import adsk.fusion
import traceback
import os.path

from .FilteredExportUtil import getComponents
from .FilteredExportUtil import renderResultMessage
from .FilteredExportUtil import FilteredExportResult

from .Fusion360Utilities.Fusion360Utilities import AppObjects
from .Fusion360Utilities.Fusion360CommandBase import Fusion360CommandBase

# Faked statics for easy code maintainance
S_CPY_SELECTION_LOOKUP='cpySelection'
S_CPY_FILTER_TYPE_LOOKUP = 'cpyDropDownFilterType'
S_CPY_FILTER_TYPET_TOP_LEVEL = 'Top level'
S_CPY_FILTER_TYPE_LEAVES = 'Leaves'
S_CPY_FILTER_TYPE_MIXED_LEAVES = 'Mixed leaves'

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
# Export top level or selected components
#
def exportTopLevelMode(appObjects, input_values):
    # get root component
    rootComponent = appObjects.design.rootComponent

    # get component list
    components = []

    # selection available?
    if S_CPY_SELECTION_LOOKUP in input_values:
        if input_values[S_CPY_SELECTION_LOOKUP][0] == rootComponent:
            # process all components
            components = getComponents(rootComponent.occurrences, components, False, False)
        else:
            # process selcted components
            components = getComponents(input_values[S_CPY_SELECTION_LOOKUP], components, False, False)
    else:
        # process all components
        components = getComponents(rootComponent.occurrences, components, False, False)

     # list of processed file names
    processedComponents = []

    # get target folder
#    documentFolder = appObjects.document.dataFile.parentFolder

    # get export path
    exportPath = getPath(appObjects)

    # export all components
    for component in components:
        fullFileName = os.path.join(exportPath, component.name) 

        stpExportOptions = appObjects.export_manager.createSTEPExportOptions(fullFileName, component)       
        appObjects.export_manager.execute(stpExportOptions)
        
        processedComponents.append(component.name)

    # return resulting lists
    return FilteredExportResult(exportPath, processedComponents, '')


#
# Export top level or selected components
#
def exportLeaveMode(appObjects, input_values):
    # get root component
    rootComponent = appObjects.design.rootComponent

    # get component list
    components = []

    # selection available?
    if S_CPY_SELECTION_LOOKUP in input_values:
        # process selcted components
        components = getComponents(input_values[S_CPY_SELECTION_LOOKUP], components, True, False)
    else:
        # process all components
        components = getComponents(rootComponent.occurrences, components, True, False)

     # list of processed and skipped file names
    processedComponents = []
    skippedComponents = []

    # get target folder
#    documentFolder = appObjects.document.dataFile.parentFolder

    # get export path
    exportPath = getPath(appObjects)

    for component in components:
        if component.bRepBodies and not component.occurrences:
            # export leave component (contains bodies but no other components)
            fullFileName = os.path.join(exportPath, component.name) 
    
            stpExportOptions = appObjects.export_manager.createSTEPExportOptions(fullFileName, component)       
            appObjects.export_manager.execute(stpExportOptions)
            
            processedComponents.append(component.name)
        elif component.bRepBodies and component.occurrencesByComponent:
            # skip export because this component contains bodies and components
            skippedComponents.append(component.name)

    # return resulting lists
    return FilteredExportResult(exportPath, processedComponents, skippedComponents)


#
# Export top mixed level or selected components
#
def exportMixedLeaveMode(appObjects, input_values):
    # get root component
    rootComponent = appObjects.design.rootComponent

    # get component list
    components = []

    # selection available?
    if S_CPY_SELECTION_LOOKUP in input_values:
        # process selcted components
        components = getComponents(input_values[S_CPY_SELECTION_LOOKUP], components, True, False)
    else:
        # process all components
        components = getComponents(rootComponent.occurrences, components, True, False)

     # list of processed and skipped file names
    processedComponents = []

    # get target folder
#    documentFolder = appObjects.document.dataFile.parentFolder

    # get export path
    exportPath = getPath(appObjects)
    
    for component in components:
        fullFileName = os.path.join(exportPath, component.name) 

        stpExportOptions = appObjects.export_manager.createSTEPExportOptions(fullFileName, component)       
        appObjects.export_manager.execute(stpExportOptions)
        
        processedComponents.append(component.name)

    # return resulting lists
    return FilteredExportResult(exportPath, processedComponents, '')


#
# Save copy as a collection of bodies
#
class FilteredExportStp(Fusion360CommandBase):
    # Run when the user presses OK
    def on_execute(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs, args, input_values):
        try:
            appObjects = AppObjects()

            # no design? Nothing to do
            if not appObjects.design:
                raise ValueError('No active Fusion design', 'No Design')

            # export components
            exportResult = None

            if input_values[S_CPY_FILTER_TYPE_LOOKUP] == S_CPY_FILTER_TYPET_TOP_LEVEL:
                # export top level mode
                exportResult = exportTopLevelMode(appObjects, input_values)
            elif input_values[S_CPY_FILTER_TYPE_LOOKUP] == S_CPY_FILTER_TYPE_LEAVES:
                # export leave mode
                exportResult = exportLeaveMode(appObjects, input_values)
            elif input_values[S_CPY_FILTER_TYPE_LOOKUP] == S_CPY_FILTER_TYPE_MIXED_LEAVES:
                # export mixed leave mode
                exportResult = exportMixedLeaveMode(appObjects, input_values)
            
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
        selectionCommand = inputs.addSelectionInput(S_CPY_SELECTION_LOOKUP, 'Select Components', '')
        selectionCommand.setSelectionLimits(0)
        selectionCommand.addSelectionFilter('Occurrences')

        # Filter type (Top level, )
        dropDownCpyFilterType = inputs.addDropDownCommandInput(S_CPY_FILTER_TYPE_LOOKUP, 'Filter Type', adsk.core.DropDownStyles.LabeledIconDropDownStyle);
        dropDownCpyFilterTypeItems = dropDownCpyFilterType.listItems
        dropDownCpyFilterTypeItems.add(S_CPY_FILTER_TYPET_TOP_LEVEL, True, '')
        dropDownCpyFilterTypeItems.add(S_CPY_FILTER_TYPE_LEAVES, False, '')
        dropDownCpyFilterTypeItems.add(S_CPY_FILTER_TYPE_MIXED_LEAVES, False, '')

    # Run whenever a user makes any change to a value or selection in the addin UI
    def on_preview(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs, args, input_values):
        pass


    # Run after the command is finished.
    def on_destroy(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs, reason, input_values):
        pass


    # Run when any input is changed.
    def on_input_changed(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs, changed_input, input_values):
        pass

