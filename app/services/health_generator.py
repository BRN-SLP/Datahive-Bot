import os
import zipfile
import tempfile
import random
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger("DatahiveBot")

def mutate_date_string(date_str, global_shift_minutes, local_variance_minutes=5):
    """
    Shifts a string date like '2021-08-04 23:12:37 +0200' by a global factor + local noise.
    """
    try:
        if len(date_str) < 25 or '+' not in date_str and '-' not in date_str[-6:]:
            return date_str

        date_part = date_str[:-6] 
        offset_part = date_str[-6:]
        
        # Apply global timeline shift + localized per-record noise
        total_shift = global_shift_minutes + random.randint(-local_variance_minutes, local_variance_minutes)
        
        dt = datetime.strptime(date_part, "%Y-%m-%d %H:%M:%S")
        dt = dt + timedelta(minutes=total_shift)
        return dt.strftime("%Y-%m-%d %H:%M:%S") + offset_part
    except Exception as e:
        return date_str

def mutate_value(val_str, global_mutation_factor, local_variance_limit=0.03):
    """
    Mutates a numerical value string by a global factor + completely random local noise (e.g., 3%).
    """
    try:
        val = float(val_str)
        # Combine global shift with local noise
        total_mutation_factor = global_mutation_factor + random.uniform(-local_variance_limit, local_variance_limit)
        
        mutation = val * total_mutation_factor
        new_val = max(0, val + mutation) # Value shouldn't realistically go below 0 (e.g. steps/pulse)
        
        if val_str.isdigit() or val_str.endswith(".0"):
            return str(int(new_val))
        else:
            # Preserve original decimal length vaguely
            decimal_places = len(val_str.split('.')[-1]) if '.' in val_str else 0
            if decimal_places == 0:
                return str(int(new_val))
            format_str = f"{{:.{min(decimal_places, 4)}f}}"
            return format_str.format(new_val)
    except:
        return val_str

def generate_unique_health_export(base_zip_path, output_zip_path, profile_id):
    """
    Reads a massive Apple Health export.zip, streams the XML, mutates it on the fly, 
    and writes it directly to a new ZIP file without blowing up RAM.
    """
    if not os.path.exists(base_zip_path):
        logger.error(f"Base health zip not found at {base_zip_path}")
        return False

    # Seed randomizer based on profile ID so the same profile always gets the same mutated file
    # This is safer than truly random on every run to avoid erratic jumps if uploaded twice
    random.seed(f"datahive_{profile_id}")
    
    # Global shifts for this specific generation
    global_time_shift = random.randint(-45, 45) # Shift entire timeline by up to 45 mins
    global_val_factor = random.uniform(-0.07, 0.07) # Adjust all biometrics by up to 7%
    
    logger.info(f"Generating Health payload for Profile {profile_id} (Shift: {global_time_shift}m, Val: {global_val_factor*100:.1f}%)")

    # We need a temp file for the XML streaming process
    temp_xml_path = tempfile.mktemp(suffix=".xml")
    
    try:
        with zipfile.ZipFile(base_zip_path, 'r') as z_in:
            # Locate the main XML file (usually apple_health_export/export.xml)
            xml_filename = None
            for name in z_in.namelist():
                if name.endswith("export.xml"):
                    xml_filename = name
                    break
            
            if not xml_filename:
                logger.error("No export.xml found in archive.")
                return False

            # Stream XML Out
            with open(temp_xml_path, 'wb') as f_out:
                f_out.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
                f_out.write(b'<!DOCTYPE HealthData [\n')
                f_out.write(b'<!-- HealthKit Export Version: 14 -->\n')
                f_out.write(b'<!ELEMENT HealthData (ExportDate,Me,(Record|Correlation|Workout|ActivitySummary|ClinicalRecord|Audiogram|VisionPrescription)*)>\n')
                f_out.write(b'<!ATTLIST HealthData locale CDATA #REQUIRED>\n')
                f_out.write(b'<!ELEMENT ExportDate EMPTY>\n')
                f_out.write(b'<!ATTLIST ExportDate value CDATA #REQUIRED>\n')
                f_out.write(b'<!ELEMENT Me EMPTY>\n')
                f_out.write(b'<!ATTLIST Me HKCharacteristicTypeIdentifierDateOfBirth CDATA #REQUIRED HKCharacteristicTypeIdentifierBiologicalSex CDATA #REQUIRED HKCharacteristicTypeIdentifierBloodType CDATA #REQUIRED HKCharacteristicTypeIdentifierFitzpatrickSkinType CDATA #REQUIRED HKCharacteristicTypeIdentifierCardioFitnessMedicationsUse CDATA #REQUIRED>\n')
                f_out.write(b'<!ELEMENT Record ((MetadataEntry|HeartRateVariabilityMetadataList)*)>\n')
                f_out.write(b'<!ATTLIST Record type CDATA #REQUIRED unit CDATA #IMPLIED value CDATA #IMPLIED sourceName CDATA #REQUIRED sourceVersion CDATA #IMPLIED device CDATA #IMPLIED creationDate CDATA #IMPLIED startDate CDATA #REQUIRED endDate CDATA #REQUIRED>\n')
                f_out.write(b'<!ELEMENT Correlation ((MetadataEntry|Record)*)>\n')
                f_out.write(b'<!ATTLIST Correlation type CDATA #REQUIRED sourceName CDATA #REQUIRED sourceVersion CDATA #IMPLIED device CDATA #IMPLIED creationDate CDATA #IMPLIED startDate CDATA #REQUIRED endDate CDATA #REQUIRED>\n')
                f_out.write(b'<!ELEMENT Workout ((MetadataEntry|WorkoutEvent|WorkoutRoute|WorkoutStatistics)*)>\n')
                f_out.write(b'<!ATTLIST Workout workoutActivityType CDATA #REQUIRED duration CDATA #IMPLIED durationUnit CDATA #IMPLIED totalDistance CDATA #IMPLIED totalDistanceUnit CDATA #IMPLIED totalEnergyBurned CDATA #IMPLIED totalEnergyBurnedUnit CDATA #IMPLIED sourceName CDATA #REQUIRED sourceVersion CDATA #IMPLIED device CDATA #IMPLIED creationDate CDATA #IMPLIED startDate CDATA #REQUIRED endDate CDATA #REQUIRED>\n')
                f_out.write(b'<!ELEMENT WorkoutActivity ((MetadataEntry)*)>\n')
                f_out.write(b'<!ATTLIST WorkoutActivity uuid CDATA #REQUIRED startDate CDATA #REQUIRED endDate CDATA #IMPLIED duration CDATA #IMPLIED durationUnit CDATA #IMPLIED>\n')
                f_out.write(b'<!ELEMENT WorkoutEvent ((MetadataEntry)*)>\n')
                f_out.write(b'<!ATTLIST WorkoutEvent type CDATA #REQUIRED date CDATA #REQUIRED duration CDATA #IMPLIED durationUnit CDATA #IMPLIED>\n')
                f_out.write(b'<!ELEMENT WorkoutStatistics EMPTY>\n')
                f_out.write(b'<!ATTLIST WorkoutStatistics type CDATA #REQUIRED startDate CDATA #REQUIRED endDate CDATA #REQUIRED average CDATA #IMPLIED minimum CDATA #IMPLIED maximum CDATA #IMPLIED sum CDATA #IMPLIED unit CDATA #IMPLIED>\n')
                f_out.write(b'<!ELEMENT WorkoutRoute ((MetadataEntry|FileReference)*)>\n')
                f_out.write(b'<!ATTLIST WorkoutRoute sourceName CDATA #REQUIRED sourceVersion CDATA #IMPLIED device CDATA #IMPLIED creationDate CDATA #IMPLIED startDate CDATA #REQUIRED endDate CDATA #REQUIRED>\n')
                f_out.write(b'<!ELEMENT FileReference EMPTY>\n')
                f_out.write(b'<!ATTLIST FileReference path CDATA #REQUIRED>\n')
                f_out.write(b'<!ELEMENT ActivitySummary EMPTY>\n')
                f_out.write(b'<!ATTLIST ActivitySummary dateComponents CDATA #IMPLIED activeEnergyBurned CDATA #IMPLIED activeEnergyBurnedGoal CDATA #IMPLIED activeEnergyBurnedUnit CDATA #IMPLIED appleMoveTime CDATA #IMPLIED appleMoveTimeGoal CDATA #IMPLIED appleExerciseTime CDATA #IMPLIED appleExerciseTimeGoal CDATA #IMPLIED appleStandHours CDATA #IMPLIED appleStandHoursGoal CDATA #IMPLIED>\n')
                f_out.write(b'<!ELEMENT MetadataEntry EMPTY>\n')
                f_out.write(b'<!ATTLIST MetadataEntry key CDATA #REQUIRED value CDATA #REQUIRED>\n')
                f_out.write(b'<!ELEMENT HeartRateVariabilityMetadataList (InstantaneousBeatsPerMinute*)>\n')
                f_out.write(b'<!ELEMENT InstantaneousBeatsPerMinute EMPTY>\n')
                f_out.write(b'<!ATTLIST InstantaneousBeatsPerMinute bpm CDATA #REQUIRED time CDATA #REQUIRED>\n')
                f_out.write(b'<!ELEMENT ClinicalRecord EMPTY>\n')
                f_out.write(b'<!ATTLIST ClinicalRecord type CDATA #REQUIRED identifier CDATA #REQUIRED sourceName CDATA #REQUIRED sourceURL CDATA #REQUIRED fhirVersion CDATA #REQUIRED receivedDate CDATA #REQUIRED resourceFilePath CDATA #REQUIRED>\n')
                f_out.write(b'<!ELEMENT Audiogram EMPTY>\n')
                f_out.write(b'<!ATTLIST Audiogram sourceName CDATA #REQUIRED sourceVersion CDATA #IMPLIED device CDATA #IMPLIED creationDate CDATA #IMPLIED startDate CDATA #REQUIRED endDate CDATA #REQUIRED>\n')
                f_out.write(b'<!ELEMENT VisionPrescription EMPTY>\n')
                f_out.write(b'<!ATTLIST VisionPrescription type CDATA #REQUIRED dateIssued CDATA #REQUIRED expirationDate CDATA #IMPLIED>\n')
                f_out.write(b']>\n')
                f_out.write(b'<HealthData locale="en_US">\n')

                # Using iterparse to memory-efficiently read the massive XML
                with z_in.open(xml_filename) as source_xml:
                    context = ET.iterparse(source_xml, events=('start', 'end'))
                    
                    for event, elem in context:
                        if event == 'end':
                            if elem.tag in ['Record', 'Workout', 'ActivitySummary', 'WorkoutEvent']:
                                
                                # Mutate Dates
                                for date_field in ['creationDate', 'startDate', 'endDate']:
                                    if date_field in elem.attrib:
                                        elem.attrib[date_field] = mutate_date_string(elem.attrib[date_field], global_time_shift)
                                
                                # Mutate Values
                                if 'value' in elem.attrib:
                                    elem.attrib['value'] = mutate_value(elem.attrib['value'], global_val_factor)
                                
                                # Write element to file manually to avoid memory buildup
                                f_out.write(ET.tostring(elem, encoding='utf-8'))
                                f_out.write(b'\n')
                                
                                # CRITICAL: Clear the element from RAM
                                elem.clear()

                    f_out.write(b'</HealthData>\n')

        # Create output ZIP and compress our mutated XML
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as z_out:
            z_out.write(temp_xml_path, arcname=xml_filename)
            
        logger.info(f"Successfully generated {output_zip_path}")
        return True

    except Exception as e:
        logger.error(f"Error mutating health data: {e}")
        return False
        
    finally:
        # Cleanup temp file
        if os.path.exists(temp_xml_path):
            os.remove(temp_xml_path)

if __name__ == "__main__":
    import sys
    # Simple CLI for testing
    if len(sys.argv) == 4:
        # python health_generator.py in.zip out.zip profile123
        logging.basicConfig(level=logging.INFO)
        generate_unique_health_export(sys.argv[1], sys.argv[2], sys.argv[3])
