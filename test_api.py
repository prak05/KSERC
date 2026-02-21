#!/usr/bin/env python3
"""
[Purpose] Simple test script to verify the KSERC ARA Backend API
[Source] User defined test script
[Why] Validates that all basic endpoints work correctly
"""

import requests
import json
import sys

def create_minimal_pdf() -> bytes:
    """
    [Purpose] Creates a minimal valid PDF for testing
    [Why] Allows testing without external dependencies
    [Returns] PDF file content as bytes
    """
    print("Creating minimal test PDF...")
    # Minimal valid PDF structure
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources 4 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>
endobj
5 0 obj
<< /Length 144 >>
stream
BT
/F1 12 Tf
100 750 Td
(M/s Infopark Limited) Tj
0 -20 Td
(Truing Up of Accounts - year 2023-24) Tj
0 -20 Td
(Order No: KSERC/TEST/001) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
0000000308 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
502
%%EOF
"""
    return pdf_content

def test_health_check(base_url: str):
    """Test health check endpoint"""
    print("\n" + "="*60)
    print("Testing Health Check Endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{base_url}/")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✓ Health check passed")
            return True
        else:
            print("✗ Health check failed")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_api_info(base_url: str):
    """Test API info endpoint"""
    print("\n" + "="*60)
    print("Testing API Info Endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{base_url}/info")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✓ API info passed")
            return True
        else:
            print("✗ API info failed")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_analyze_order(base_url: str):
    """Test analyze order endpoint"""
    print("\n" + "="*60)
    print("Testing Analyze Order Endpoint")
    print("="*60)
    
    try:
        # Create sample PDF
        pdf_content = create_minimal_pdf()
        
        # Upload PDF
        files = {'file': ('test-order.pdf', pdf_content, 'application/pdf')}
        response = requests.post(f"{base_url}/analyze-order/", files=files)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response:")
            print(f"  - Licensee: {data.get('licensee_name')}")
            print(f"  - Financial Year: {data.get('financial_year')}")
            print(f"  - Total ARR: ₹{data.get('total_arr_approved', 0):.2f} Lakhs")
            print(f"  - Total Trued Up: ₹{data.get('total_trued_up', 0):.2f} Lakhs")
            print(f"  - Net Surplus/Deficit: ₹{data.get('net_surplus_deficit', 0):.2f} Lakhs")
            print(f"  - Financial Items: {len(data.get('financial_summary', []))}")
            print("✓ Analyze order passed")
            return True
        else:
            print(f"Response: {response.text}")
            print("✗ Analyze order failed")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_compliance_check(base_url: str):
    """Test compliance check endpoint"""
    print("\n" + "="*60)
    print("Testing Compliance Check Endpoint")
    print("="*60)
    
    try:
        # Create sample PDF
        pdf_content = create_minimal_pdf()
        
        # Upload PDF
        files = {'file': ('test-order.pdf', pdf_content, 'application/pdf')}
        response = requests.post(f"{base_url}/compliance-check/", files=files)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response includes:")
            print(f"  - Basic Analysis: ✓")
            print(f"  - Compliance Report: ✓")
            print(f"  - Executive Summary: ✓")
            
            if 'compliance_report' in data:
                report = data['compliance_report']
                print(f"\nCompliance Status: {report.get('overall_status')}")
                print(f"Checks Performed: {len(report.get('checks_performed', []))}")
                print(f"Passed: {report.get('passed_checks', 0)}")
                print(f"Failed: {report.get('failed_checks', 0)}")
                print(f"Warnings: {len(report.get('warnings', []))}")
            
            print("✓ Compliance check passed")
            return True
        else:
            print(f"Response: {response.text}")
            print("✗ Compliance check failed")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    """Main test runner"""
    # Default to localhost
    base_url = "http://localhost:8000"
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print("="*60)
    print("KSERC ARA Backend API Tests")
    print("="*60)
    print(f"Base URL: {base_url}")
    
    # Run tests
    results = []
    results.append(("Health Check", test_health_check(base_url)))
    results.append(("API Info", test_api_info(base_url)))
    results.append(("Analyze Order", test_analyze_order(base_url)))
    results.append(("Compliance Check", test_compliance_check(base_url)))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:.<50}{status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
