import subprocess
import json
import os
import hashlib
from datetime import datetime
import logging

class ImageAuthenticityChecker:
    def __init__(self, exiftool_path="C:\exiftool\exiftool\exiftool.exe"):
        self.exiftool_path = exiftool_path
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('authenticity_check.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def extract_metadata(self, image_path):
        """Extract metadata using ExifTool"""
        try:
            result = subprocess.run(
                [self.exiftool_path, "-j", image_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                with open("metadata.json", "w") as json_file:
                    json.dump(json.loads(result.stdout)[0], json_file, separators=(',', ':'))
                return json.loads(result.stdout)[0]
            else:
                self.logger.error(f"ExifTool error: {result.stderr}")
                return None
                
        except Exception as e:
            self.logger.error(f"Metadata extraction failed: {e}")
            return None
    
    def check_basic_integrity(self, metadata):
        """Check basic file integrity and structure"""
        checks = {
            'valid_file_type': False,
            'reasonable_size': False,
            'has_metadata': False,
            'consistent_dates': False
        }
        
        # File type check
        if metadata.get('FileType') in ['PNG', 'JPEG', 'JPG', 'TIFF']:
            checks['valid_file_type'] = True
        
        # File size check (rough validation)
        if 'FileSize' in metadata:
            size_str = metadata['FileSize']
            if 'kB' in size_str:
                size_kb = int(size_str.split(' kB')[0])
                checks['reasonable_size'] = 1 <= size_kb <= 50000
            elif 'MB' in size_str:
                size_mb = float(size_str.split(' MB')[0])
                checks['reasonable_size'] = 0.001 <= size_mb <= 50
        
        # Metadata presence
        checks['has_metadata'] = len(metadata) > 5
        
        # Date consistency
        date_fields = ['FileModifyDate', 'FileCreateDate', 'DateTimeOriginal']
        existing_dates = [metadata.get(field) for field in date_fields if field in metadata]
        if len(existing_dates) >= 2:
            # Basic date format validation
            checks['consistent_dates'] = all('202' in str(date) for date in existing_dates)
        
        return checks
    
    def check_c2pa_authenticity(self, metadata):
        """Check C2PA provenance data"""
        c2pa_checks = {
            'has_c2pa_manifest': False,
            'valid_signature': False,
            'hash_validation': False,
            'ai_disclosure': False,
            'validation_passed': False
        }
        
        # C2PA presence
        c2pa_indicators = ['c2pa', 'JUMD', 'ActiveManifestUrl', 'ClaimSignatureUrl']
        c2pa_checks['has_c2pa_manifest'] = any(
            any(indicator.lower() in str(key).lower() or indicator.lower() in str(value).lower()
                for key, value in metadata.items())
            for indicator in c2pa_indicators
        )
        
        # Digital signature
        c2pa_checks['valid_signature'] = 'ClaimSignatureUrl' in metadata
        
        # Hash validation
        c2pa_checks['hash_validation'] = 'ActiveManifestHash' in metadata
        
        # AI disclosure
        ai_keywords = ['generative ai', 'google ai', 'algorithmicmedia', 'created']
        c2pa_checks['ai_disclosure'] = any(
            any(keyword in str(value).lower() 
                for value in metadata.values() 
                if value is not None)
            for keyword in ai_keywords
        )
        
        # Validation results
        if 'ValidationResultsActiveManifestSuccessCode' in metadata:
            validation_codes = metadata['ValidationResultsActiveManifestSuccessCode']
            critical_validations = ['signingCredential', 'timeStamp', 'claimSignature']
            c2pa_checks['validation_passed'] = any(
                any(critical in code for code in validation_codes)
                for critical in critical_validations
            )
        
        return c2pa_checks
    
    def check_ai_indicators(self, metadata):
        """Detect AI generation indicators"""
        ai_checks = {
            'explicit_ai_credit': False,
            'generative_actions': False,
            'digital_source_type': False,
            'creation_tools': False
        }
        
        # Explicit AI credits
        ai_credits = ['Credit', 'Creator', 'Software', 'ProcessingSoftware']
        for field in ai_credits:
            if field in metadata:
                value = str(metadata[field]).lower()
                if any(ai_term in value for ai_term in ['ai', 'generative', 'stable diffusion', 'midjourney', 'dall-e', 'google ai']):
                    ai_checks['explicit_ai_credit'] = True
        
        # Generative actions
        if 'ActionsDescription' in metadata:
            desc = metadata['ActionsDescription']
            if any(term in desc for term in ['generative', 'created', 'ai']):
                ai_checks['generative_actions'] = True
        
        # Digital source type
        if 'DigitalSourceType' in metadata:
            ds_type = str(metadata['DigitalSourceType']).lower()
            if 'algorithmicmedia' in ds_type:
                ai_checks['digital_source_type'] = True
        
        # Creation tools
        if 'Claim_Generator_InfoName' in metadata:
            ai_checks['creation_tools'] = True
        
        return ai_checks
    
    def check_tampering_indicators(self, metadata):
        """Check for signs of tampering"""
        tampering_checks = {
            'inconsistent_software': False,
            'multiple_editors': False,
            'metadata_stripping': False,
            'date_anomalies': False
        }
        
        # Check for multiple editing software
        software_fields = ['Software', 'ProcessingSoftware', 'CreatorTool']
        software_used = []
        for field in software_fields:
            if field in metadata and metadata[field]:
                software_used.append(metadata[field])
        
        tampering_checks['multiple_editors'] = len(set(software_used)) > 2
        
        # Metadata stripping (very few fields for a processed image)
        field_count = len(metadata)
        tampering_checks['metadata_stripping'] = field_count < 10 and 'FileType' in metadata
        
        # Date anomalies
        date_fields = ['DateTimeOriginal', 'CreateDate', 'ModifyDate']
        existing_dates = [metadata.get(field) for field in date_fields if field in metadata]
        if len(existing_dates) >= 2:
            # Check if dates are in reverse order (modify before create)
            try:
                dates_parsed = []
                for date_str in existing_dates:
                    # Simple date extraction (you might want more robust parsing)
                    if '202' in date_str:
                        year = int(date_str[0:4])
                        dates_parsed.append(year)
                
                if len(dates_parsed) >= 2:
                    tampering_checks['date_anomalies'] = dates_parsed != sorted(dates_parsed)
            except:
                pass
        
        return tampering_checks
    
    def calculate_authenticity_score(self, integrity_checks, c2pa_checks, ai_checks, tampering_checks):
        """Calculate overall authenticity score"""
        total_checks = 0
        passed_checks = 0
        
        # Basic integrity (weight: 30%)
        integrity_weight = 0.3
        integrity_score = sum(integrity_checks.values()) / len(integrity_checks)
        
        # C2PA verification (weight: 40%)
        c2pa_weight = 0.4
        c2pa_score = sum(c2pa_checks.values()) / len(c2pa_checks) if any(c2pa_checks.values()) else 0
        
        # AI disclosure (weight: 20%)
        ai_weight = 0.2
        ai_score = sum(ai_checks.values()) / len(ai_checks)
        
        # Tampering detection (weight: 10%, negative impact)
        tampering_weight = 0.1
        tampering_score = 1 - (sum(tampering_checks.values()) / len(tampering_checks))
        
        overall_score = (
            integrity_score * integrity_weight +
            c2pa_score * c2pa_weight +
            ai_score * ai_weight +
            tampering_score * tampering_weight
        ) * 100
        
        return min(100, overall_score)
    
    def generate_report(self, image_path, metadata, score, checks):
        """Generate comprehensive authenticity report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'image_path': image_path,
            'file_size': metadata.get('FileSize', 'Unknown'),
            'file_type': metadata.get('FileType', 'Unknown'),
            'authenticity_score': score,
            'verdict': self.get_verdict(score),
            'detailed_checks': checks,
            'recommendations': self.get_recommendations(checks, score)
        }
        
        return report
    
    def get_verdict(self, score):
        """Get authenticity verdict based on score"""
        if score >= 80:
            return "HIGH_CONFIDENCE_AUTHENTIC"
        elif score >= 60:
            return "MODERATE_CONFIDENCE"
        elif score >= 40:
            return "LOW_CONFIDENCE"
        else:
            return "POTENTIALLY_MANIPULATED"
    
    def get_recommendations(self, checks, score):
        """Generate recommendations based on check results"""
        recommendations = []
        
        if score < 60:
            recommendations.append("Exercise caution when using this image")
        
        if not checks['c2pa']['has_c2pa_manifest']:
            recommendations.append("No digital provenance data found")
        
        if checks['tampering']['multiple_editors']:
            recommendations.append("Multiple editing tools detected - verify source")
        
        if checks['ai']['explicit_ai_credit'] and score < 70:
            recommendations.append("AI-generated content - verify intended use")
        
        return recommendations
    
    def analyze_image(self, image_path):
        """Main analysis function - returns dict for backend processing"""
        self.logger.info(f"Analyzing image: {image_path}")
        
        # Extract metadata
        metadata = self.extract_metadata(image_path)
        if not metadata:
            return {"error": "Could not extract metadata"}
        
        # Perform all checks
        integrity_checks = self.check_basic_integrity(metadata)
        c2pa_checks = self.check_c2pa_authenticity(metadata)
        ai_checks = self.check_ai_indicators(metadata)
        tampering_checks = self.check_tampering_indicators(metadata)
        
        # Calculate score
        score = self.calculate_authenticity_score(
            integrity_checks, c2pa_checks, ai_checks, tampering_checks
        )
        
        # Generate report
        checks = {
            'integrity': integrity_checks,
            'c2pa': c2pa_checks,
            'ai': ai_checks,
            'tampering': tampering_checks
        }
        
        report = self.generate_report(image_path, metadata, score, checks)
        
        return report
    
    def get_report_as_strings(self, report):
        """Convert report to list of strings for backend integration"""
        output_strings = []
        
        score = report['authenticity_score']
        verdict = report['verdict']
        
        # Header
        output_strings.append("=" * 50)
        output_strings.append("IMAGE AUTHENTICITY REPORT")
        output_strings.append("=" * 50)
        
        # Score and rating
        if score >= 80:
            rating = "[EXCELLENT]"
        elif score >= 60:
            rating = "[GOOD]" 
        elif score >= 40:
            rating = "[CAUTION]"
        else:
            rating = "[SUSPICIOUS]"
        
        output_strings.append(f"Authenticity Confidence: {rating} ({score:.1f}%)\n")
        output_strings.append(f"Verdict: {verdict}\n")
        
        # File info
        output_strings.append(f"File: {os.path.basename(report['image_path'])}\n")
        output_strings.append(f"Type: {report['file_type']} | Size: {report['file_size']}\n")
        
        # Key findings
        output_strings.append("\nKEY FINDINGS:")
        
        checks = report['detailed_checks']
        
        if checks['c2pa']['has_c2pa_manifest']:
            output_strings.append("[PASS] Digital Provenance: This image has verified origin data\n")
        else:
            output_strings.append("[FAIL] Digital Provenance: No verified origin data found\n")
        
        if any(checks['ai'].values()):
            output_strings.append("[AI] AI Indicators: Signs of AI generation detected\n")
        else:
            output_strings.append("[NATURAL] Natural Image: No clear AI generation signs\n")
        
        if any(checks['tampering'].values()):
            output_strings.append("[WARNING] Editing Signs: Possible modifications detected\n")
        else:
            output_strings.append("[OK] Minimal Editing: No significant alterations found\n")
        
        # Recommendations
        if report['recommendations']:
            output_strings.append("\nRECOMMENDATIONS:")
            for rec in report['recommendations']:
                output_strings.append(f"* {rec}")
        
        return output_strings
    
    def analyze_and_format_report(self, image_path):
        """Convenience method that analyzes image and returns formatted strings"""
        report = self.analyze_image(image_path)
        if 'error' in report:
            return [f"Error: {report['error']}"]
        
        return self.get_report_as_strings(report)


class BatchAuthenticityChecker:
    def __init__(self, exiftool_path="exiftool"):
        self.checker = ImageAuthenticityChecker(exiftool_path)
    
    def analyze_directory(self, directory_path):
        """Analyze all images in a directory - returns list of reports"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.webp']
        results = []
        
        for filename in os.listdir(directory_path):
            if any(filename.lower().endswith(ext) for ext in image_extensions):
                image_path = os.path.join(directory_path, filename)
                
                try:
                    report = self.checker.analyze_image(image_path)
                    results.append(report)
                except Exception as e:
                    results.append({"error": f"Failed to analyze {filename}: {str(e)}"})
        
        return results
    
    def generate_summary_report(self, results):
        """Generate summary report for batch analysis - returns list of strings"""
        summary_strings = []
        
        valid_results = [r for r in results if 'authenticity_score' in r]
        
        if not valid_results:
            return ["No valid images analyzed"]
        
        summary = {
            'total_images': len(valid_results),
            'average_score': 0,
            'score_distribution': {'high': 0, 'medium': 0, 'low': 0, 'suspicious': 0},
            'c2pa_images': 0,
            'ai_generated_images': 0
        }
        
        scores = []
        for result in valid_results:
            score = result['authenticity_score']
            scores.append(score)
            
            # Categorize scores
            if score >= 80:
                summary['score_distribution']['high'] += 1
            elif score >= 60:
                summary['score_distribution']['medium'] += 1
            elif score >= 40:
                summary['score_distribution']['low'] += 1
            else:
                summary['score_distribution']['suspicious'] += 1
            
            # Count C2PA images
            if result['detailed_checks']['c2pa']['has_c2pa_manifest']:
                summary['c2pa_images'] += 1
            
            # Count AI images
            if any(result['detailed_checks']['ai'].values()):
                summary['ai_generated_images'] += 1
        
        if scores:
            summary['average_score'] = sum(scores) / len(scores)
        
        # Format summary as strings
        summary_strings.append("=" * 60)
        summary_strings.append("BATCH ANALYSIS SUMMARY")
        summary_strings.append("=" * 60)
        summary_strings.append(f"Total Images Analyzed: {summary['total_images']}")
        summary_strings.append(f"Average Authenticity Score: {summary['average_score']:.1f}%")
        summary_strings.append(f"C2PA-Enabled Images: {summary['c2pa_images']}")
        summary_strings.append(f"AI-Generated Images: {summary['ai_generated_images']}")
        summary_strings.append(f"Score Distribution:")
        summary_strings.append(f"  High Confidence (80-100%): {summary['score_distribution']['high']}")
        summary_strings.append(f"  Medium Confidence (60-79%): {summary['score_distribution']['medium']}")
        summary_strings.append(f"  Low Confidence (40-59%): {summary['score_distribution']['low']}")
        summary_strings.append(f"  Suspicious (0-39%): {summary['score_distribution']['suspicious']}")
        
        return summary_strings
    
    def analyze_directory_with_summary(self, directory_path):
        """Analyze directory and return both individual reports and summary"""
        individual_reports = self.analyze_directory(directory_path)
        summary_strings = self.generate_summary_report(individual_reports)
        
        # Format individual reports as strings
        all_output = []
        for report in individual_reports:
            if 'error' in report:
                all_output.append(f"ERROR: {report['error']}")
            else:
                report_strings = self.checker.get_report_as_strings(report)
                all_output.extend(report_strings)
                all_output.append("")  # Add spacing between reports
        
        all_output.extend(summary_strings)
        return all_output


def quick_check(image_path):
    """Quick check function that returns a string result"""
    checker = ImageAuthenticityChecker()
    report = checker.analyze_image(image_path)
    
    if 'error' in report:
        return f"Error analyzing image: {report['error']}"
    
    score = report.get('authenticity_score', 0)
    verdict = report.get('verdict', 'UNKNOWN')
    
    if score >= 70:
        return f"PASS: Likely Authentic ({score:.1f}%)"
    elif score >= 50:
        return f"WARNING: Use with Caution ({score:.1f}%)"
    else:
        return f"FAIL: Potential Issues ({score:.1f}%)"


def get_detailed_report(image_path):
    """Get detailed report as list of strings"""
    checker = ImageAuthenticityChecker()
    return checker.analyze_and_format_report(image_path)


def batch_analyze_directory(directory_path):
    """Batch analyze directory and return list of strings"""
    batch_checker = BatchAuthenticityChecker()
    return batch_checker.analyze_directory_with_summary(directory_path)


# Usage examples for backend integration:
if __name__ == "__main__":
    # Single image analysis
    image_path = "./image.jpg"
    
    # Quick result (returns string)
    quick_result = quick_check(image_path)
    print(quick_result)
    
    # Detailed report (returns list of strings)
    detailed_report = get_detailed_report(image_path)
    for line in detailed_report:
        print(line)
    
    # Batch analysis (returns list of strings)
    # directory = r"C:\Users\adema\OneDrive\Desktop\pdf reader"
    # batch_results = batch_analyze_directory(directory)
    # for line in batch_results:
    #     print(line)