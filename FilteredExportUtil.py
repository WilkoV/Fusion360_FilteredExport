import adsk.core
import adsk.fusion

#
# get all child occurences (components) recursively from a component
# and return a unique list of components
#
def getComponents(occurences, components, includeSubComponents, filterLinkedComponents):
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
                    if component == occurence.component:
                        # component exisits in filted list. No need to process
                        # the full list
                        componentFound = True
                        break
    
                # if occurence not found in unique list of components, add this
                # occurence because it's new
                if not componentFound and occurence.component:
                    components.append(occurence.component)
    
                # if this occurence has sub components process them, too
                if occurence.childOccurrences and not componentFound and includeSubComponents:
                    components = getComponents(occurence.childOccurrences, components, includeSubComponents, filterLinkedComponents)

    return components


#
# render result string showing path, exported objects and skipped objects
#
def renderResultMessage(exportResult):
    # Initialize with path
    resultMessage = 'Path:\n   ' + exportResult.exportPath + '\n'
    
    # render list of processed files   
    resultMessage += 'Processed:\n'
    for export in exportResult.exportNames:
        resultMessage += '   ' + export + '\n'
    
    if len(exportResult.skippedNames) == 0:
        return resultMessage
        
    # render list of processed files   
    resultMessage += 'Skipped:\n'
    for export in exportResult.skippedNames:
        resultMessage += '   ' + export + '\n'
       
    return resultMessage

#
# result set from a stl export
#
class FilteredExportResult(object):
    def __init__(self, exportPath, exportNames, skippedNames):
        self.exportPath = exportPath
        self.exportNames = exportNames
        self.skippedNames = skippedNames
