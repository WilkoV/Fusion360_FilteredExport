# Importing sample Fusion Command
# Could import multiple Command definitions here
from .FilteredExportAsStlCommand import FilteredExportAsStlCommand
from .FilteredExportSaveCopyAs import FilteredExportSaveCopyAs
from .FilteredExportStp import FilteredExportStp

commands = []
command_definitions = []

# Define parameters for stl export command
cmd = {
    'cmd_name': 'Filtered STL Export',
    'cmd_description': 'Exports all or selected components without creating duplicate exports',
    'cmd_id': 'cmdID_filteredExportStl08',
    'cmd_resources': './resources/exportStl',
    'workspace': 'FusionSolidEnvironment',
    'toolbar_panel_id': 'SolidScriptsAddinsPanel',
    'class': FilteredExportAsStlCommand
}
command_definitions.append(cmd)

# Define parameters for stp export command
cmd = {
    'cmd_name': 'Filtered STP Export',
    'cmd_description': 'Export of all or selected components',
    'cmd_id': 'cmdID_filteredStpExport10',
    'cmd_resources': './resources/exportStp',
    'workspace': 'FusionSolidEnvironment',
    'toolbar_panel_id': 'SolidScriptsAddinsPanel',
    'class': FilteredExportStp
}
command_definitions.append(cmd)

# Define parameters for save copy as command
cmd = {
    'cmd_name': 'Filtered Save Copy As',
    'cmd_description': 'Saves a copy of all or selected components',
    'cmd_id': 'cmdID_filteredCopyAs09',
    'cmd_resources': './resources/saveCopyAs',
    'workspace': 'FusionSolidEnvironment',
    'toolbar_panel_id': 'SolidScriptsAddinsPanel',
    'class': FilteredExportSaveCopyAs
}
command_definitions.append(cmd)



# Set to True to display various useful messages when debugging your app
debug = False

# Don't change anything below here:
for cmd_def in command_definitions:
    command = cmd_def['class'](cmd_def, debug)
    commands.append(command)
    

def run(context):
    for run_command in commands:
        run_command.on_run()


def stop(context):
    for stop_command in commands:
        stop_command.on_stop()
