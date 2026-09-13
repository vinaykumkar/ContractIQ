"""Generate demo contract files for presentations.

Self-contained: everything lives in demo_contracts/ and nothing in the app
reads this folder. Run with the project venv:

    .venv\\Scripts\\python.exe demo_contracts\\generate_demo_contracts.py

Outputs 12 DOCX agreements (+ 3 PDF versions) with varied risk profiles so
analyses show LOW / MEDIUM / HIGH risk bands during a demo.
"""
from pathlib import Path

from docx import Document
from docx.shared import Pt
import fitz  # PyMuPDF

OUT = Path(__file__).resolve().parent

# ---------------------------------------------------------------- helpers
def para(doc, text, bold=False, size=11):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.bold = bold
    return p

def build_docx(spec):
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Georgia"
    style.font.size = Pt(10.5)
    doc.add_heading(spec["title"], level=1)
    para(doc, spec["preamble"])
    for i, (head, body) in enumerate(spec["sections"], start=1):
        doc.add_heading(f"{i}. {head}", level=2)
        para(doc, body)
    doc.add_paragraph()
    para(doc, "IN WITNESS WHEREOF, the Parties have executed this Agreement as of the Effective Date.")
    doc.add_paragraph()
    sig = doc.add_paragraph("_____________________________")
    para(doc, spec["party_a"], bold=True)
    doc.add_paragraph("_____________________________")
    para(doc, spec["party_b"], bold=True)
    path = OUT / f"{spec['file']}.docx"
    doc.save(path)
    return path

def build_pdf(spec):
    doc = fitz.open()
    lines = [spec["title"].upper(), ""]
    def emit(text):
        lines.extend(text.split("\n"))
        lines.append("")
    emit(spec["preamble"])
    for i, (head, body) in enumerate(spec["sections"], start=1):
        emit(f"{i}. {head.upper()}")
        emit(body)
    emit("IN WITNESS WHEREOF, the Parties have executed this Agreement as of the Effective Date.")
    emit("_____________________________          _____________________________")
    emit(f"{spec['party_a']}                                 {spec['party_b']}")
    page = doc.new_page()
    y = 60
    for ln in lines:
        while len(ln) > 95:
            page.insert_text((50, y), ln[:95], fontsize=9, fontname="times-roman")
            ln = ln[95:]
            y += 13
        page.insert_text((50, y), ln, fontsize=9 if not ln.isupper() or y > 70 else 13,
                         fontname="times-roman")
        y += 13
        if y > 780:
            page = doc.new_page()
            y = 60
    path = OUT / f"{spec['file']}.pdf"
    doc.save(str(path))
    doc.close()
    return path

# ---------------------------------------------------------------- contracts
C = []

C.append(dict(
    file="01_saas_subscription_low_risk",
    title="SaaS Subscription Agreement",
    party_a="Cloudpine Software Inc.",
    party_b="Meridian Studios LLC",
    preamble=("This SaaS Subscription Agreement (the \"Agreement\") is entered into as of January 12, 2026 "
              "(the \"Effective Date\"), by and between Cloudpine Software Inc., a Washington corporation "
              "(\"Vendor\"), and Meridian Studios LLC, an Oregon limited liability company (\"Customer\"). "
              "The initial term of this Agreement is twelve (12) months and expires on January 12, 2027, unless "
              "terminated earlier in accordance with the terms below."),
    sections=[
        ("Subscription and Access",
         "Vendor grants Customer a non-exclusive, non-transferable right during the Term to access and use the "
         "Cloudpine design platform in accordance with the documentation and the number of authorized users "
         "purchased. Upon payment, Vendor also grants Customer a limited license to use the accompanying mobile "
         "applications solely for Customer's internal business purposes."),
        ("Fees and Payment",
         "Customer shall pay the subscription fees set out in Order Form No. 1 within thirty (30) days of invoice. "
         "Fees are non-refundable except as expressly stated in this Agreement."),
        ("Renewal",
         "This Agreement shall not auto-renew. Any renewal term must be agreed in a signed order form executed by "
         "both Parties at least thirty (30) days before the expiry of the then-current term."),
        ("Termination",
         "Either Party may terminate this Agreement for convenience upon sixty (60) days' prior written notice to "
         "the other Party. Either Party may also terminate immediately for material breach that remains uncured "
         "fifteen (15) days after written notice."),
        ("Assignment",
         "Customer may assign this Agreement in whole in connection with a merger, acquisition or sale of "
         "substantially all assets upon written notice to Vendor; no other consent is required."),
        ("Audit Rights",
         "Vendor may, upon thirty (30) days' prior written notice and no more than once per year, audit Customer's "
         "usage records during normal business hours to verify compliance with user limits."),
        ("Limitation of Liability",
         "Neither Party shall be liable for indirect or consequential damages. Vendor's total aggregate liability "
         "arising out of this Agreement shall not exceed the subscription fees paid by Customer in the twelve (12) "
         "months preceding the claim."),
        ("Insurance",
         "Vendor shall maintain commercial general liability insurance with coverage of at least $1,000,000 per "
         "occurrence throughout the Term and shall provide certificates of insurance on request."),
        ("Governing Law",
         "This Agreement is governed by the laws of the State of Washington, without regard to conflict-of-laws "
         "principles. The Parties submit to the exclusive jurisdiction of the state and federal courts located in "
         "King County, Washington."),
    ],
))

C.append(dict(
    file="02_mutual_nda_low_risk",
    title="MUTUAL NON-DISCLOSURE AGREEMENT",
    party_a="Helix Robotics Ltd.",
    party_b="Crestpoint Advisors LLP",
    preamble=("This Mutual Non-Disclosure Agreement (the \"Agreement\") is made and entered into as of "
              "February 3, 2026 (the \"Effective Date\"), by and between Helix Robotics Ltd., a United Kingdom "
              "private company limited by shares, and Crestpoint Advisors LLP, a Texas limited liability "
              "partnership (each a \"Party\" and together the \"Parties\"). The Agreement continues in force for "
              "two (2) years from the Effective Date and expires on February 3, 2028."),
    sections=[
        ("Purpose",
         "The Parties wish to explore a potential business relationship (the \"Purpose\") and may disclose "
         "Confidential Information to each other in connection with the Purpose."),
        ("Confidential Information",
         "\"Confidential Information\" means non-public information disclosed by one Party to the other that is "
         "designated confidential or that reasonably should be understood to be confidential, including technical "
         "data, product plans and business terms."),
        ("Obligations",
         "The receiving Party shall use Confidential Information solely for the Purpose, protect it with at least "
         "the care it uses for its own confidential information, and not disclose it to third parties except to "
         "employees and advisers bound by equivalent obligations."),
        ("Exclusions",
         "Confidential Information does not include information that is or becomes public through no breach, was "
         "rightfully known before disclosure, is independently developed, or is rightfully received from a third "
         "party without duty of confidentiality."),
        ("Term and No Renewal",
         "The confidentiality obligations survive for three (3) years after the expiry or termination of this "
         "Agreement. This Agreement does not contain any automatic renewal; any extension requires a fresh signed "
         "writing."),
        ("Termination",
         "Either Party may terminate this Agreement for convenience upon thirty (30) days' written notice, "
         "provided that termination does not relieve either Party of obligations with respect to Confidential "
         "Information already received."),
        ("Remedies and Governing Law",
         "The Parties acknowledge that unauthorized disclosure may cause irreparable harm for which damages are "
         "inadequate, entitling the disclosing Party to seek injunctive relief. This Agreement is governed by the "
         "laws of the State of Texas."),
    ],
))

C.append(dict(
    file="03_freelance_contractor_low_risk",
    title="Freelance Contractor Agreement",
    party_a="Brightline Media LLC",
    party_b="Priya Raman (Independent Contractor)",
    preamble=("This Freelance Contractor Agreement (the \"Agreement\") is entered into effective June 1, 2026 "
              "(the \"Effective Date\"), by and between Brightline Media LLC, an Illinois limited liability "
              "company (\"Company\"), and Priya Raman, an independent contractor (\"Contractor\"). The engagement "
              "runs for six (6) months and ends on November 30, 2026 (the \"Term\"), unless extended in writing."),
    sections=[
        ("Services",
         "Contractor shall provide content design and illustration services as described in one or more written "
         "statements of work. Contractor controls the manner and means of performing the Services."),
        ("Deliverables and License",
         "Upon full payment, Contractor grants Company an exclusive, perpetual, worldwide license to use, modify "
         "and display the deliverables in Company's marketing. Contractor retains ownership of portfolio rights."),
        ("Compensation",
         "Company shall pay Contractor a fixed fee of $4,500 per statement of work, invoiced monthly and payable "
         "net fifteen (15) days. No benefits, equity or employment protections are provided."),
        ("Term Extension",
         "The Term does not renew automatically. Any extension requires a written amendment signed by both "
         "Parties before the Term ends."),
        ("Termination",
         "Either Party may terminate this Agreement for convenience upon fourteen (14) days' written notice. "
         "Company shall pay for Services performed up to the termination date."),
        ("Assignment",
         "Contractor may not subcontract or assign performance of the Services without Company's prior written "
         "consent, which may be given by email."),
        ("Independent Contractor Status",
         "Contractor is not an employee, partner or joint venturer of Company and is solely responsible for "
         "Contractor's own taxes and insurance."),
        ("Limitation of Liability",
         "Each Party's aggregate liability under this Agreement shall not exceed the total amounts paid or "
         "payable under the applicable statement of work."),
        ("Governing Law",
         "This Agreement is governed by the laws of the State of Illinois; the Parties consent to the courts of "
         "Cook County, Illinois."),
    ],
))

C.append(dict(
    file="04_commercial_lease_medium_risk",
    title="COMMERCIAL LEASE AGREEMENT",
    party_a="Granite Row Properties Inc. (Landlord)",
    party_b="Novara Fitness Co. (Tenant)",
    preamble=("This Commercial Lease Agreement (the \"Lease\") is made and entered into as of April 18, 2026 "
              "(the \"Effective Date\"), by and between Granite Row Properties Inc., an Arizona corporation "
              "(\"Landlord\"), and Novara Fitness Co., a Colorado limited liability company (\"Tenant\"). The "
              "initial term is thirty-six (36) months commencing July 1, 2026 and expiring on June 30, 2029."),
    sections=[
        ("Premises",
         "Landlord leases to Tenant approximately 2,400 square feet of retail space at 214 Granite Row, Suite 3, "
         "Boulder, Colorado (the \"Premises\"), for use as a fitness studio and no other purpose without "
         "Landlord's written consent."),
        ("Rent and Deposit",
         "Tenant shall pay base rent of $4,850 per month, due on the first day of each month, plus Tenant's "
         "pro-rata share of common area maintenance. A security deposit of $9,700 shall be held by Landlord."),
        ("Renewal",
         "This Lease shall automatically renew for successive twelve (12) month periods at the then-market rate "
         "unless either Party gives written notice of non-renewal at least ninety (90) days before the end of the "
         "then-current term."),
        ("Assignment and Subletting",
         "Tenant shall not assign this Lease or sublet all or part of the Premises without Landlord's prior "
         "written consent, which shall not be unreasonably withheld. Any purported assignment without consent is "
         "void."),
        ("Insurance",
         "Tenant shall maintain commercial general liability insurance of not less than $2,000,000 per occurrence "
         "naming Landlord as additional insured, and shall provide certificates before taking possession."),
        ("Landlord's Access and Audit",
         "Landlord may access the Premises upon twenty-four (24) hours' notice for inspection, and may once per "
         "year audit Tenant's gross-revenue reports where percentage rent applies."),
        ("Default",
         "Tenant is in default if rent is unpaid five (5) days after written notice, or if any other covenant is "
         "breached and remains uncured for thirty (30) days. There is no right to terminate for convenience."),
        ("Limitation of Liability",
         "Landlord shall not be liable for Tenant's business losses, and in no event shall Landlord's aggregate "
         "liability exceed the rent paid in the six (6) months preceding the claim."),
        ("Governing Law",
         "This Lease is governed by the laws of the State of Colorado; exclusive venue lies in Boulder County."),
    ],
))

C.append(dict(
    file="05_consulting_services_medium_risk",
    title="Consulting Services Agreement",
    party_a="Oakfield Health Group PC",
    party_b="Stratwin Consulting Ltd.",
    preamble=("This Consulting Services Agreement (the \"Agreement\") is entered into as of May 9, 2026 (the "
              "\"Effective Date\") by and between Oakfield Health Group PC, a Michigan professional corporation "
              "(\"Client\"), and Stratwin Consulting Ltd., a Delaware limited liability company (\"Consultant\"). "
              "The initial term is twenty-four (24) months."),
    sections=[
        ("Engagement",
         "Client engages Consultant to provide operational-efficiency consulting services described in Project "
         "Charter A, and Consultant accepts such engagement under the terms of this Agreement."),
        ("Statement of Work and License",
         "Each deliverable prepared by Consultant for Client is licensed to Client upon full payment under a "
         "perpetual, non-transferable, internal-use license; Consultant retains all pre-existing intellectual "
         "property."),
        ("Term and Renewal",
         "This Agreement shall automatically renew for successive one (1) year renewal terms unless either Party "
         "gives written notice of non-renewal at least sixty (60) days before the end of the then-current term."),
        ("Termination for Convenience",
         "Client may terminate this Agreement for convenience upon forty-five (45) days' written notice, paying "
         "only for Services rendered through the termination date. Consultant may terminate for convenience upon "
         "ninety (90) days' notice."),
        ("Assignment",
         "Neither Party may assign this Agreement without the prior written consent of the other Party, except to "
         "an affiliate or in connection with a reorganization upon notice."),
        ("Records and Audit",
         "Consultant shall keep records of time and expenses for twelve (12) months; Client may audit such records "
         "once per contract year on fifteen (15) days' notice."),
        ("Confidentiality and Non-Compete",
         "Consultant shall not, during the Term and for six (6) months afterwards, provide competing operational "
         "consulting services to any healthcare provider operating within fifty miles of Client's facilities if "
         "such engagement would use Client's confidential information."),
        ("Limitation of Liability",
         "Neither Party is liable for indirect damages, and each Party's aggregate liability shall not exceed the "
         "fees paid or payable in the twelve (12) months preceding the claim."),
        ("Insurance",
         "Consultant shall maintain professional liability (errors and omissions) insurance of not less than "
         "$2,000,000 in the aggregate and commercial general liability insurance of $1,000,000 per occurrence."),
        ("Governing Law",
         "This Agreement is governed by the laws of the State of Michigan, without regard to its conflict-of-laws "
         "rules."),
    ],
))

C.append(dict(
    file="06_supply_vendor_medium_risk",
    title="Exclusive Supply and Vendor Agreement",
    party_a="Kestrel Baking Co.",
    party_b="Sunhollow Farms Cooperative",
    preamble=("This Exclusive Supply and Vendor Agreement (the \"Agreement\") is entered into as of March 22, "
              "2026 (the \"Effective Date\"), between Kestrel Baking Co., a Nevada corporation (\"Purchaser\"), "
              "and Sunhollow Farms Cooperative, an agricultural cooperative organized under Nevada law "
              "(\"Supplier\"). The initial term runs until March 21, 2027."),
    sections=[
        ("Appointment and Exclusivity",
         "Purchaser appoints Supplier as its exclusive supplier of organic stone-milled flour, and Purchaser "
         "agrees that it shall not purchase flour meeting this specification from any other supplier during the "
         "Term without Supplier's prior written consent."),
        ("Orders and Delivery",
         "Supplier shall deliver weekly quantities per the rolling forecast annexed hereto. Title and risk pass on "
         "delivery to Purchaser's facility."),
        ("License to Branding Materials",
         "Supplier grants Purchaser a limited, non-exclusive license to use Supplier's farm mark in Purchaser's "
         "point-of-sale materials describing product provenance during the Term."),
        ("Term and Automatic Renewal",
         "This Agreement automatically renews for successive twelve (12) month terms unless either Party gives "
         "written notice of non-renewal at least one hundred twenty (120) days before the end of the then-current "
         "term."),
        ("Assignment",
         "Neither Party may assign this Agreement or any of its rights hereunder without the other Party's prior "
         "written consent, except in connection with the sale of all substantially related assets."),
        ("Termination",
         "This Agreement may be terminated for uncured material breach on thirty (30) days' notice. There is no "
         "termination for convenience; Purchaser's minimum purchase commitments survive for the full Term."),
        ("Limitation of Liability",
         "Supplier shall not be liable for lost profits, and Supplier's aggregate liability shall not exceed the "
         "amounts paid by Purchaser in the three (3) months preceding the claim."),
        ("Insurance",
         "Supplier shall maintain product liability insurance of not less than $2,000,000 per occurrence and "
         "provide certificates annually."),
        ("Governing Law",
         "This Agreement is governed by the laws of the State of Nevada; venue lies in Washoe County."),
    ],
))

C.append(dict(
    file="07_employment_agreement_high_risk",
    title="EMPLOYMENT AGREEMENT (EXECUTIVE)",
    party_a="Vertex Analytics Inc. (Company)",
    party_b="Daniel Okafor (Employee)",
    preamble=("This Employment Agreement (the \"Agreement\") is entered into effective September 1, 2026 (the "
              "\"Effective Date\"), by and between Vertex Analytics Inc., a New York corporation (the "
              "\"Company\"), and Daniel Okafor (\"Employee\"). Employment under this Agreement continues for an "
              "initial term ending September 1, 2028, subject to earlier termination as provided herein."),
    sections=[
        ("Position and Duties",
         "Employee shall serve as Director of Data Science and shall devote substantially all of Employee's "
         "professional time to the Company. The Company may assign comparable duties from time to time."),
        ("Compensation and Benefits",
         "The Company shall pay an annual base salary of $185,000, subject to an annual bonus of up to 20% at the "
         "Board's discretion, and standard benefits per Company policy."),
        ("Confidential Information",
         "Employee shall hold all Company confidential information in strict confidence during and after "
         "employment and shall return all materials upon separation."),
        ("Non-Compete",
         "During employment and for twelve (12) months after separation, Employee shall not, directly or "
         "indirectly, provide services to, or engage in, any business that competes with the Company's data-"
         "analytics platforms in the United States."),
        ("Exclusive Services",
         "During employment, Employee shall provide services on a full-time exclusive basis to the Company and "
         "shall not accept any other professional engagement without the Company's prior written approval."),
        ("Assignment of Inventions",
         "Employee hereby assigns to the Company all right, title and interest in inventions made during "
         "employment relating to the Company's business, and agrees to reasonably assist in securing intellectual "
         "property protection; Employee cannot assign this obligation."),
        ("Term and Non-Renewal",
         "This Agreement does not automatically renew; continuation of employment beyond the term requires a new "
         "written agreement executed before the term ends."),
        ("Termination",
         "The Company may terminate employment for cause immediately upon written notice. Employee acknowledges "
         "this Agreement provides no right to terminate for convenience; resignation requires sixty (60) days' "
         "advance written notice."),
        ("Limitation of Liability",
         "The Company's aggregate liability to Employee under this Agreement shall not exceed twelve (12) months "
         "of base salary."),
        ("Governing Law",
         "This Agreement is governed by the laws of the State of New York, without regard to conflict-of-laws "
         "principles."),
    ],
))

C.append(dict(
    file="08_distribution_agreement_high_risk",
    title="Exclusive Distribution Agreement",
    party_a="Auralis Instruments GmbH (Manufacturer)",
    party_b="Redcliff Trading Company (Distributor)",
    preamble=("This Exclusive Distribution Agreement (the \"Agreement\") is entered into as of February 26, 2026 "
              "(the \"Effective Date\"), by and between Auralis Instruments GmbH, a company organized under the "
              "laws of Germany (\"Manufacturer\"), and Redcliff Trading Company, a Massachusetts corporation "
              "(\"Distributor\"). The initial term is three (3) years, expiring February 25, 2029."),
    sections=[
        ("Appointment; Exclusive Territory",
         "Manufacturer appoints Distributor as its exclusive distributor of the laboratory balance product line "
         "in the six New England states (the \"Territory\"), and Distributor accepts that appointment."),
        ("Non-Compete",
         "During the Term and for two (2) years thereafter, Distributor shall not, within the Territory, market, "
         "sell or otherwise deal in any measuring-instrument products that compete with the Products."),
        ("Minimum Purchase and Renewal",
         "Distributor shall purchase not less than $750,000 of Products per contract year. This Agreement "
         "automatically renews for successive two (2) year renewal terms provided minimum purchases were met and "
         "neither Party gives non-renewal notice at least ninety (90) days before expiry."),
        ("Trademarks and License",
         "Manufacturer grants Distributor a non-exclusive, non-transferable, revocable license to use the "
         "Auralis trademarks solely in promoting the Products within the Territory during the Term."),
        ("Assignment",
         "Distributor may not assign this Agreement or the rights granted hereunder, whether by operation of law "
         "or otherwise, without Manufacturer's prior written consent."),
        ("Termination",
         "Either Party may terminate for uncured material breach. Neither Party may terminate for convenience "
         "during the first two (2) contract years; thereafter convenience termination requires one hundred eighty "
         "(180) days' notice and payment of outstanding minimums."),
        ("Post-Termination Obligations",
         "Upon termination, Distributor shall cease use of the trademarks, return confidential information, and "
         "may sell remaining inventory for ninety (90) days at standard prices."),
        ("Limitation of Liability",
         "Manufacturer's aggregate liability shall not exceed the amounts actually received for Products in the "
         "six (6) months preceding the claim; consequential damages are excluded."),
        ("Insurance",
         "Distributor shall maintain product liability insurance of not less than $3,000,000 per occurrence, with "
         "Manufacturer as additional insured."),
        ("Governing Law",
         "This Agreement is governed by the laws of the State of Massachusetts, excluding its conflict-of-laws "
         "rules and the United Nations Convention on Contracts for the International Sale of Goods."),
    ],
))

C.append(dict(
    file="09_franchise_agreement_high_risk",
    title="FRANCHISE AGREEMENT",
    party_a="Brewline Coffee Inc. (Franchisor)",
    party_b="Harbor & 5th Hospitality LLC (Franchisee)",
    preamble=("This Franchise Agreement (the \"Agreement\") is entered into as of June 30, 2026 (the \"Effective "
              "Date\"), by and between Brewline Coffee Inc., a Florida corporation (\"Franchisor\"), and Harbor & "
              "5th Hospitality LLC, a Florida limited liability company (\"Franchisee\"), for the operation of a "
              "Brewline Coffee franchised location at 950 Seawall Drive, Tampa, Florida."),
    sections=[
        ("Grant of Franchise",
         "Franchisor grants Franchisee the right, and Franchisee accepts the obligation, to operate one (1) "
         "Brewline Coffee franchised business at the Approved Location for the Term, using Franchisor's marks, "
         "systems and confidential operations manual, under a non-transferable license limited to the Approved "
         "Location."),
        ("Term and Renewal",
         "The initial term is ten (10) years, expiring June 30, 2036. This Agreement automatically renews for "
         "successive five (5) year renewal terms if Franchisee is in good standing, has completed renovations "
         "required by Franchisor, and signs the then-current form of franchise agreement at least one hundred "
         "eighty (180) days before expiry."),
        ("Fees",
         "Franchisee shall pay an initial franchise fee of $40,000 (non-refundable), a continuing royalty of 6% "
         "of gross revenues, and a brand-development contribution of 2% of gross revenues, all monthly in "
         "arrears."),
        ("Non-Compete",
         "During the Term and for two (2) years after it ends, Franchisee, its owners and managers shall not own, "
         "operate or be engaged in any coffee or quick-service beverage business within three (3) miles of the "
         "Approved Location or any other Brewline location."),
        ("Exclusive Products and Suppliers",
         "Franchisee shall purchase all coffee, packaging and approved supplies exclusively from Franchisor or "
         "Franchisor-designated suppliers, and shall not offer any product or service not listed in the "
         "confidential operations manual."),
        ("Assignment",
         "Franchisee may not assign this Agreement or any interest in the franchise entity without Franchisor's "
         "prior written consent; a transfer fee of $7,500 applies to any approved assignment."),
        ("Default and Termination",
         "Franchisor may terminate this Agreement on ten (10) days' notice for uncured payment default, on thirty "
         "(30) days' notice for uncured operational defaults, and immediately for abandonment or health-code "
         "violations endangering the public. Franchisee has no right to terminate for convenience."),
        ("Insurance",
         "Franchisee shall maintain commercial general liability insurance of $2,000,000 per occurrence, property "
         "insurance at full replacement value, and workers' compensation as required by law, naming Franchisor as "
         "additional insured."),
        ("Limitation of Liability",
         "Franchisor's aggregate liability to Franchisee shall not exceed the franchise fee actually paid under "
         "this Agreement."),
        ("Governing Law",
         "This Agreement is governed by the laws of the State of Florida, and Franchisee consents to venue in "
         "Hillsborough County, Florida."),
    ],
))

C.append(dict(
    file="10_partnership_llc_medium_risk",
    title="LLC OPERATING AGREEMENT (TWO MEMBERS)",
    party_a="Ines Kolar (Member)",
    party_b="Tobin Reyes (Member)",
    preamble=("This Limited Liability Company Operating Agreement (the \"Agreement\") is adopted as of January "
              "20, 2026 (the \"Effective Date\") by the members of Fernwell Design Workshop LLC, a Colorado "
              "limited liability company (the \"Company\"). The Company's existence continues until dissolved "
              "under this Agreement or by law; the operating period through December 31, 2028 (the \"Initial "
              "Operating Term\") reflects the Members' business plan."),
    sections=[
        ("Formation and Purpose",
         "The Members formed the Company under the Colorado Revised Uniform Limited Liability Company Act to "
         "provide architectural visualization and 3D-rendering services."),
        ("Capital Contributions",
         "Ines Kolar contributes $30,000 and Tobin Reyes contributes $30,000; ownership interests are 50% each. "
         "No Member may assign or pledge all or part of the Member's interest without the other Member's written "
         "consent, which shall not be unreasonably withheld."),
        ("Management",
         "The Company is member-managed. Ordinary decisions require a simple majority; new lines of business, "
         "debt over $25,000 and admission of new members require unanimous consent."),
        ("Distributions and Renewal of Plan",
         "Profits and losses are allocated equally. The Members shall review the business plan annually; the "
         "Initial Operating Term does not renew automatically and continuation requires a written plan amendment."),
        ("Restrictive Covenants",
         "While a Member and for one (1) year after withdrawal, no Member shall directly solicit Company clients "
         "for competing visualization services within the Denver metropolitan area."),
        ("Withdrawal and Dissolution",
         "A Member may withdraw upon ninety (90) days' written notice; the remaining Member may continue the "
         "Company by purchasing the withdrawing Member's interest at fair value per the annexed schedule."),
        ("Insurance",
         "The Company shall maintain commercial general liability insurance of not less than $1,000,000 per "
         "occurrence and professional liability insurance of $1,000,000."),
        ("Limitation of Liability",
         "Members' liability is limited as provided by Colorado law, and no Member shall be liable for Company "
         "obligations beyond the Member's capital contribution except for willful misconduct."),
        ("Governing Law",
         "This Agreement is governed by the laws of the State of Colorado."),
    ],
))

C.append(dict(
    file="11_loan_agreement_low_risk",
    title="PROMISSORY NOTE AND LOAN AGREEMENT",
    party_a="Fidellar Credit Union (Lender)",
    party_b="Willowmere Learning Inc. (Borrower)",
    preamble=("This Loan Agreement and Promissory Note (the \"Agreement\") is entered into as of May 2, 2026 "
              "(the \"Effective Date\"), between Fidellar Credit Union, a state-chartered credit union "
              "(\"Lender\"), and Willowmere Learning Inc., a California nonprofit public benefit corporation "
              "(\"Borrower\"). The loan matures on May 2, 2031, and is not subject to any renewal term."),
    sections=[
        ("Loan Amount and Purpose",
         "Lender agrees to lend Borrower $150,000 (the \"Loan\") to finance classroom technology described in "
         "Exhibit A. Borrower shall use the Loan solely for that purpose."),
        ("Interest and Repayment",
         "The Loan bears interest at 6.25% per annum, amortized over sixty (60) months in equal monthly "
         "installments of $2,923.44, beginning June 1, 2026. There is no automatic renewal of this Agreement."),
        ("Prepayment",
         "Borrower may prepay the Loan in whole or in part at any time without premium or penalty."),
        ("Security",
         "The Loan is secured by the equipment described in Exhibit A under a security agreement; Borrower shall "
         "insure such equipment at full replacement value, with Lender named as loss payee."),
        ("Covenants and Financial Audit",
         "Borrower shall deliver annual financial statements within ninety (90) days of fiscal year end. Lender "
         "may review Borrower's financial records upon ten (10) business days' notice, no more than once per "
         "year."),
        ("Events of Default and Termination Rights",
         "Non-payment beyond ten (10) days after written notice, breach of covenants uncured for thirty (30) "
         "days, or insolvency are events of default entitling Lender to accelerate the Loan. Borrower has no "
         "right to prepay-and-terminate the relationship for convenience other than full repayment."),
        ("Assignment",
         "Borrower may not assign this Agreement or the equipment. Lender may assign its interest to another "
         "regulated lender upon written notice."),
        ("Governing Law",
         "This Agreement is governed by the laws of the State of California; venue lies in Alameda County."),
    ],
))

C.append(dict(
    file="12_software_license_medium_risk",
    title="Enterprise Software License Agreement",
    party_a="Norvant Systems Ltd. (Licensor)",
    party_b="Pallas Insurance Group (Licensee)",
    preamble=("This Enterprise Software License Agreement (the \"Agreement\") is entered into as of August 14, "
              "2026 (the \"Effective Date\"), between Norvant Systems Ltd., an Irish private company limited by "
              "shares (\"Licensor\"), and Pallas Insurance Group, a Connecticut corporation (\"Licensee\"). The "
              "license term is three (3) years, ending August 13, 2029."),
    sections=[
        ("Grant of License",
         "Licensor grants Licensee a non-exclusive, non-transferable, non-sublicensable license during the Term "
         "to install and use the Norvant claims-analytics platform, in object-code form only, for Licensee's "
         "internal business operations up to the licensed user count."),
        ("Fees",
         "Licensee shall pay an annual license fee of $96,000, invoiced yearly in advance, plus implementation "
         "fees as per Schedule 2."),
        ("Term and Renewal",
         "This Agreement automatically renews for successive one (1) year terms at the then-current list price "
         "unless Licensee gives written notice of non-renewal at least ninety (90) days before the end of the "
         "then-current term."),
        ("Support and Updates",
         "Licensor shall provide standard support (business-hours, next-business-day response) and make updates "
         "generally available to licensees at no additional charge."),
        ("Assignment",
         "Licensee may not assign, sublicense or otherwise transfer any rights under this Agreement without "
         "Licensor's prior written consent; any prohibited assignment is void."),
        ("Termination",
         "Licensor may terminate for uncured payment default on fifteen (15) days' notice; Licensee may terminate "
         "for convenience at the end of any contract year on ninety (90) days' notice with payment of the "
        "then-current annual fee."),
        ("Audit Rights",
         "Licensor may, no more than once per year and upon twenty (20) business days' notice, audit Licensee's "
         "usage during business hours to verify compliance with the licensed user count."),
        ("Limitation of Liability",
         "Excluding breaches of confidentiality and license misuse, each Party's aggregate liability shall not "
         "exceed the fees paid in the twelve (12) months preceding the claim."),
        ("Insurance",
         "Licensor shall maintain cyber-liability insurance of not less than $5,000,000 and commercial general "
         "liability insurance of $2,000,000 per occurrence."),
        ("Governing Law",
         "This Agreement is governed by the laws of Ireland; the Parties submit to the courts of Dublin, "
         "Ireland."),
    ],
))

C.append(dict(
    file="13_joint_venture_agreement_high_risk",
    title="JOINT VENTURE AGREEMENT",
    party_a="Terraforge Energy Corp.",
    party_b="Solvenia Grid Technologies SAS",
    preamble=("This Joint Venture Agreement (the \"Agreement\") is entered into as of April 7, 2026 (the "
              "\"Effective Date\"), by and between Terraforge Energy Corp., a Delaware corporation, and Solvenia "
              "Grid Technologies SAS, a French société par actions simplifiée (each a \"Venture Partner\"). The "
              "parties hereby form Windrow Junction JV LLC (the \"Venture\") to develop, own and operate utility-"
              "scale battery storage projects in the United States. The Venture continues until December 31, "
              "2033, unless terminated as provided herein."),
    sections=[
        ("Formation and Purpose",
         "The Venture Partners have formed the Venture under Delaware law exclusively to develop, finance, "
         "construct, own and operate battery storage facilities identified in Exhibit A, and for no other "
         "purpose without unanimous Venture Partner approval."),
        ("Capital Contributions",
         "Terraforge shall contribute $6,000,000 and Solvenia shall contribute $6,000,000 plus specified "
         "technology licenses, in the installments set out in Exhibit B. Additional capital requires unanimous "
         "consent; dilution applies to a non-funding partner under Exhibit C."),
        ("Non-Compete",
         "During the Venture's existence and for three (3) years thereafter, neither Venture Partner nor its "
         "affiliates shall, without the other's written consent, develop or operate competing utility-scale "
         "battery storage projects within a fifty (50) mile radius of any Venture project."),
        ("Exclusivity of Technology",
         "Solvenia grants the Venture the exclusive right to use its grid-conversion technology within the "
         "Territory, and Solvenia shall not license the technology to any third party for projects in the "
         "Territory during the Term. Solvenia further agrees the Venture shall be its exclusive customer for "
         "integration services in the Territory."),
        ("License to Venture",
         "Solvenia hereby grants the Venture a perpetual, non-transferable, royalty-free license to use its "
         "proprietary control software solely for operating the Venture projects."),
        ("Term and Renewal of Project Rights",
         "The site-control rights in Exhibit A automatically renew for successive two (2) year extension periods "
         "unless the Venture gives written notice of abandonment at least sixty (60) days before each extension "
         "date."),
        ("Transfer of Interests",
         "No Venture Partner may sell, pledge, hypothecate or otherwise transfer all or any part of its interest "
         "in the Venture without the prior written consent of the other Venture Partner, which may be withheld in "
         "its sole discretion; any prohibited transfer is void."),
        ("Term; No Convenience Exit",
         "Neither Venture Partner may withdraw or terminate its participation for convenience; exit is possible "
         "only through a buy-sell offer pursuant to Article 12 or upon a customary event of default."),
        ("Limitation of Liability",
         "Except for fraud, willful misconduct or breach of Articles 4 or 5, each Venture Partner's aggregate "
         "liability to the other shall not exceed its capital contribution to the Venture."),
        ("Governing Law",
         "This Agreement is governed by the laws of the State of Delaware, without regard to conflict-of-laws "
         "principles."),
    ],
))

C.append(dict(
    file="14_reseller_agreement_low_risk",
    title="Non-Exclusive Reseller Agreement",
    party_a="Lumendra AV Inc. (Manufacturer)",
    party_b="Stagecraft AV Solutions (Reseller)",
    preamble=("This Non-Exclusive Reseller Agreement (the \"Agreement\") is entered into as of July 8, 2026 (the "
              "\"Effective Date\"), between Lumendra AV Inc., a California corporation (\"Manufacturer\"), and "
              "Stagecraft AV Solutions, a sole proprietorship (\"Reseller\"). The initial term is one (1) year, "
              "ending July 7, 2027."),
    sections=[
        ("Appointment",
         "Manufacturer appoints Reseller as a non-exclusive reseller of Lumendra wireless presentation systems "
         "in Reseller's normal course of business, and Reseller accepts that appointment. Manufacturer may "
         "appoint other resellers at any time."),
        ("Purchases",
         "Reseller shall purchase inventory at the standard reseller discount (35% off list) per purchase orders "
         "accepted by Manufacturer. Minimum purchases apply only to the first order."),
        ("Termination",
         "Either Party may terminate this Agreement for convenience upon thirty (30) days' written notice. "
         "Reseller may return unopened inventory at cost within thirty (30) days after termination."),
        ("End-User Warranty Pass-Through",
         "Manufacturer's standard two (2) year end-user warranty passes through to end customers; Reseller shall "
         "not modify or extend it without written consent."),
        ("License to Marketing Materials",
         "Manufacturer grants Reseller a non-exclusive, revocable license to use Lumendra trademarks and product "
         "imagery solely to promote the Products during the Term."),
        ("Assignment",
         "Reseller may assign this Agreement to a successor of its business upon written notice; Manufacturer may "
         "assign freely."),
        ("Limitation of Liability",
         "Manufacturer's aggregate liability shall not exceed the amounts Reseller actually paid for the "
         "Products giving rise to the claim."),
        ("Insurance",
         "Reseller shall maintain commercial general liability insurance of $500,000 per occurrence."),
        ("Governing Law",
         "This Agreement is governed by the laws of the State of California; venue lies in Santa Clara County."),
    ],
))

C.append(dict(
    file="15_real_estate_purchase_agreement_low_risk",
    title="COMMERCIAL REAL ESTATE PURCHASE AND SALE AGREEMENT",
    party_a="Corliss Holdings LP (Seller)",
    party_b="Ferrostrand Capital LLC (Buyer)",
    preamble=("This Purchase and Sale Agreement (the \"Agreement\") is made and entered into as of September 3, "
              "2026 (the \"Effective Date\"), by and between Corliss Holdings LP, a Delaware limited partnership "
              "(\"Seller\"), and Ferrostrand Capital LLC, a New York limited liability company (\"Buyer\"), for "
              "the purchase and sale of the warehouse property at 1180 Tannery Road, Newark, New Jersey (the "
              "\"Property\"). This Agreement terminates automatically at the Outside Closing Date of December 15, "
              "2026, unless the closing has occurred; there is no renewal."),
    sections=[
        ("Purchase and Sale",
         "Seller agrees to sell and Buyer agrees to purchase the Property, together with all improvements and "
         "fixtures, for a purchase price of $4,250,000 (the \"Purchase Price\"), payable at closing by wire "
         "transfer."),
        ("Earnest Money",
         "Within three (3) business days of the Effective Date, Buyer shall deposit $125,000 with Granite Title "
         "Escrow (\"Escrow Agent\") as earnest money, credited against the Purchase Price at closing."),
        ("Due Diligence",
         "Buyer shall have forty-five (45) days from the Effective Date to inspect the Property, review title and "
         "environmental reports, and may terminate for any reason during that period by notice to Escrow Agent, "
         "receiving a full refund of earnest money."),
        ("Assignment",
         "Buyer may assign this Agreement to an affiliate or to a single-purpose entity formed to acquire the "
         "Property upon written notice; Seller may assign to a partnership affiliate."),
        ("Termination Rights",
         "In addition to due-diligence termination, either Party may terminate if the closing has not occurred by "
         "the Outside Closing Date due to the other Party's uncured default; the prevailing party receives the "
         "earnest money as its sole and exclusive remedy, subject to the cap in Section 8."),
        ("Brokerage",
         "Each Party represents that no broker is involved except Harborline Commercial Realty, representing "
         "Buyer at Seller's expense per Exhibit D."),
        ("Limitation of Liability",
         "Notwithstanding anything to the contrary, each Party's aggregate liability arising out of this "
         "Agreement shall not exceed the earnest money deposit."),
        ("Governing Law",
         "This Agreement is governed by the laws of the State of New Jersey; venue lies in Essex County."),
    ],
))

C.append(dict(
    file="16_influencer_creator_agreement_medium_risk",
    title="Content Creator and Influencer Agreement",
    party_a="Vantala Sportswear Inc. (Brand)",
    party_b="Casey Lindqvist (Creator)",
    preamble=("This Content Creator and Influencer Agreement (the \"Agreement\") is entered into as of August 1, "
              "2026 (the \"Effective Date\"), between Vantala Sportswear Inc., an Oregon corporation (\"Brand\"), "
              "and Casey Lindqvist, an individual content creator (\"Creator\"). The initial campaign term runs "
              "six (6) months, through January 31, 2027."),
    sections=[
        ("Deliverables",
         "Creator shall produce and publish the sponsored content set out in Campaign Brief A: two (2) Instagram "
         "reels, three (3) Instagram stories with link stickers, and one (1) long-form YouTube video per month, "
         "each meeting the brand-safety guidelines attached."),
        ("Category Exclusivity",
         "During the Term and for sixty (60) days afterwards, Creator shall not accept, wear or promote products "
         "from any athletic footwear or sportswear brand other than Vantala in any public content, and Brand "
         "shall be the exclusive sportswear sponsor of Creator's channels."),
        ("Usage License",
         "Creator grants Brand a non-exclusive, worldwide, royalty-free license to reuse, edit and republish the "
         "sponsored content in Brand's own marketing for twenty-four (24) months from publication; all other "
         "rights remain with Creator."),
        ("Compensation",
         "Brand shall pay a monthly retainer of $6,500 plus a 10% commission on tracked sales, payable net "
         "thirty (30) days with creator-provided invoices."),
        ("Term Extension and Renewal",
         "If both Parties are performing satisfactorily, this Agreement automatically renews for successive "
         "three (3) month renewal terms on the same terms unless either Party gives notice of non-renewal at "
         "least thirty (30) days before the end of the then-current term."),
        ("Exclusivity of Channel Team",
         "Creator shall not delegate content production under this Agreement to any third-party agency or assign "
         "the benefit of this Agreement without Brand's prior written consent."),
        ("Termination",
         "Either Party may terminate for uncured material breach on fourteen (14) days' notice; Brand may "
         "terminate for convenience on thirty (30) days' notice paying earned but unpaid amounts, but Creator "
         "has no convenience termination right during a renewal term."),
        ("Morals Clause",
         "Brand may suspend or terminate immediately if Creator engages in conduct reasonably likely to damage "
         "Brand's reputation, in which case Brand pays only amounts earned through the termination date."),
        ("Limitation of Liability",
         "Each Party's aggregate liability under this Agreement shall not exceed the total compensation paid or "
         "payable in the three (3) months preceding the claim."),
        ("Governing Law",
         "This Agreement is governed by the laws of the State of Oregon; venue lies in Multnomah County."),
    ],
))

C.append(dict(
    file="17_manufacturing_agreement_medium_risk",
    title="Toll Manufacturing Agreement",
    party_a="Brightcove Chemicals Corp. (Customer)",
    party_b="Faraday Processing Partners LLC (Manufacturer)",
    preamble=("This Toll Manufacturing Agreement (the \"Agreement\") is entered into as of March 13, 2026 (the "
              "\"Effective Date\"), between Brightcove Chemicals Corp., a Texas corporation (\"Customer\"), and "
              "Faraday Processing Partners LLC, a Louisiana limited liability company (\"Manufacturer\"). "
              "Manufacturer shall process Customer-supplied raw materials into finished specialty polymers per "
              "the attached specifications. The initial term is two (2) years, ending March 12, 2028."),
    sections=[
        ("Processing Services",
         "Manufacturer shall convert Customer's raw materials into finished goods conforming to Specification "
         "Sheet 7 at the tolling fee per kilogram in Schedule 1, meeting the agreed yield and quality targets."),
        ("Materials and Title",
         "Title to raw materials and finished goods remains with Customer at all times; Manufacturer bears the "
         "risk of loss only while in its custody."),
        ("License to Process Technology",
         "Solely to perform the Services, Customer grants Manufacturer a limited, non-transferable, royalty-free "
         "license to use Customer's process parameters for the Term; no other rights are granted."),
        ("Capacity and Renewal",
         "Manufacturer shall reserve a minimum monthly capacity of 40,000 kg. This Agreement automatically "
         "renews for successive one (1) year renewal terms unless either Party gives notice of non-renewal at "
         "least ninety (90) days before the end of the then-current term."),
        ("Assignment",
         "Neither Party may assign this Agreement without the other's prior written consent, except to an "
         "affiliate or successor of substantially all assets upon notice."),
        ("Termination",
         "Either Party may terminate for convenience upon one hundred eighty (180) days' written notice; orders "
         "in production at the time of notice shall be completed and paid."),
        ("Records and Audit",
         "Manufacturer shall keep batch records, yield data and materials-consumption logs for five (5) years; "
         "Customer may audit them twice per contract year on ten (10) business days' notice."),
        ("Insurance",
         "Manufacturer shall maintain commercial general liability insurance of $5,000,000 per occurrence, "
         "pollution liability insurance of $5,000,000, and property insurance covering Customer's materials in "
         "its custody."),
        ("Limitation of Liability",
         "Neither Party shall be liable for consequential damages; Manufacturer's aggregate liability for "
         "physical damage to Customer materials shall not exceed the replacement cost of the affected batch."),
        ("Governing Law",
         "This Agreement is governed by the laws of the State of Texas; venue lies in Harris County."),
    ],
))

C.append(dict(
    file="18_research_collaboration_low_risk",
    title="Research Collaboration Agreement",
    party_a="Delamere University (University)",
    party_b="Phosphene Photonics Inc. (Company)",
    preamble=("This Research Collaboration Agreement (the \"Agreement\") is entered into as of October 5, 2026 "
              "(the \"Effective Date\"), between Delamere University, a Massachusetts nonprofit institution of "
              "higher education (\"University\"), and Phosphene Photonics Inc., a Massachusetts corporation "
              "(\"Company\"). The collaboration runs for eighteen (18) months, ending April 4, 2028, and does "
              "not automatically renew; any extension requires a written amendment."),
    sections=[
        ("Research Program",
         "University shall perform the research program described in the annexed Statement of Work under the "
         "direction of Professor A. Ferreira (the \"Principal Investigator\"), using reasonable efforts "
         "consistent with academic practice."),
        ("Research Results and License",
         "Company receives a first option to negotiate an exclusive commercial license to inventions arising "
         "solely from the program; University retains ownership and the right to use Research Results for "
         "teaching and further non-commercial research, and to publish after the review period in Section 5."),
        ("Publication",
         "University may publish Research Results after providing Company a sixty (60) day review copy; Company "
         "may request a further sixty (60) day delay to pursue patent protection, once per manuscript."),
        ("Term and Termination",
         "Either Party may terminate this Agreement for convenience upon sixty (60) days' written notice, in "
         "which case Company pays costs incurred through the termination date. Termination does not revoke "
         "licenses already granted to embodied results."),
        ("Confidentiality",
         "Confidential Information exchanged for the program is protected for five (5) years from disclosure and "
         "may be shared only with personnel bound by similar obligations."),
        ("Assignment",
         "Neither Party may assign this Agreement without the other's prior written consent, except to a "
         "successor of substantially all related assets where the assignee assumes this Agreement in writing."),
        ("Limitation of Liability",
         "Each Party's aggregate liability arising out of this Agreement shall not exceed the research fees paid "
         "or payable in the twelve (12) months preceding the claim; neither Party is liable for the other's lost "
         "profits."),
        ("Insurance",
         "Each Party shall maintain insurance as customary for institutions of its type; Company shall carry "
         "commercial general liability insurance of at least $1,000,000 per occurrence."),
        ("Governing Law",
         "This Agreement is governed by the laws of the Commonwealth of Massachusetts."),
    ],
))

C.append(dict(
    file="19_equipment_rental_agreement_medium_risk",
    title="Equipment Rental Agreement",
    party_a="Trellis Lift Rentals Inc. (Owner)",
    party_b="Corvane Construction LLC (Renter)",
    preamble=("This Equipment Rental Agreement (the \"Agreement\") is entered into as of February 9, 2026 (the "
              "\"Effective Date\"), between Trellis Lift Rentals Inc., a Utah corporation (\"Owner\"), and "
              "Corvane Construction LLC, a Utah limited liability company (\"Renter\"), for the rental of the "
              "equipment listed in Schedule A (the \"Equipment\") for use at Renter's project site in Salt Lake "
              "City, Utah. The base rental term runs twelve (12) months through February 8, 2027."),
    sections=[
        ("Rental and Use",
         "Owner rents to Renter the Equipment in good working order. Renter shall use the Equipment only at the "
         "Site, only for its intended purpose, and only under qualified operators."),
        ("Rent and Renewal",
         "Renter shall pay monthly rent of $3,200 per unit. After the base term, this Agreement automatically "
         "renews month-to-month at the same rates unless either Party gives at least thirty (30) days' written "
         "notice of non-renewal."),
        ("Delivery, Inspection and Acceptance",
         "Renter shall inspect the Equipment on delivery and notify Owner of defects within twenty-four (24) "
         "hours; continued use constitutes acceptance."),
        ("Maintenance, Damage and Insurance",
         "Renter is responsible for routine maintenance and all damage other than normal wear, and shall insure "
         "the Equipment at full replacement value with Owner as loss payee, plus commercial general liability "
         "insurance of $1,000,000 per occurrence."),
        ("Subletting and Assignment",
         "Renter shall not sublet, lend or assign the Equipment or this Agreement without Owner's prior written "
         "consent; the Equipment remains personal property of Owner notwithstanding attachment to realty."),
        ("Termination",
         "Renter may terminate the base term for convenience on sixty (60) days' notice with payment of a "
         "one-time early-return charge of two (2) months' rent; Owner may terminate for default on ten (10) "
         "days' notice with immediate repossession rights."),
        ("Limitation of Liability",
         "Owner is not a manufacturer and makes no warranties beyond pass-through of manufacturer warranties; "
         "Owner's aggregate liability shall not exceed three (3) months of rent paid."),
        ("Governing Law",
         "This Agreement is governed by the laws of the State of Utah; venue lies in Salt Lake County."),
    ],
))

C.append(dict(
    file="20_data_processing_agreement_low_risk",
    title="Data Processing Agreement (GDPR Service Annex)",
    party_a="Sunniva Analytics ApS (Processor)",
    party_b="Halbrook Retail Group plc (Controller)",
    preamble=("This Data Processing Agreement (the \"DPA\") is annexed to and forms part of the Master Analytics "
              "Services Agreement between the Parties dated September 18, 2026 (the \"Effective Date\"), between "
              "Sunniva Analytics ApS, a Danish company (\"Processor\"), and Halbrook Retail Group plc, a United "
              "Kingdom public limited company (\"Controller\"). The DPA applies for as long as Processor processes "
              "Controller Personal Data under the Master Agreement and follows its term; it contains no separate "
              "renewal mechanism."),
    sections=[
        ("Roles and Scope",
         "Controller acts as data controller and Processor as data processor (Article 28 GDPR) with respect to "
         "the customer-behavior analytics data described in Annex I, which includes pseudonymized identifiers and "
         "transaction events of Controller's customers in the EEA and UK."),
        ("Documented Instructions",
         "Processor shall process Controller Personal Data only on Controller's documented instructions, "
         "including transfers to the subprocessors listed in Annex II, unless required by EU or Member State law."),
        ("Confidentiality and Staff",
         "Processor shall ensure persons authorized to process the data are bound by confidentiality obligations "
         "and receive appropriate data-protection training."),
        ("Security Measures",
         "Processor shall implement the technical and organizational measures in Annex III, including encryption "
         "in transit and at rest, access controls, and pseudonymization."),
        ("Subprocessors",
         "Controller grants general written authorization for the subprocessors in Annex II; Processor shall give "
         "thirty (30) days' notice of changes, during which Controller may object on reasonable data-protection "
         "grounds."),
        ("Assistance, Audit and Data Subject Rights",
         "Processor shall assist Controller with data subject requests and impact assessments, and shall make "
         "audit reports available annually; Controller may conduct an on-site audit once per year on thirty (30) "
         "days' notice."),
        ("Breach Notification",
         "Processor shall notify Controller without undue delay, and in any event within forty-eight (48) hours, "
         "after becoming aware of a personal data breach."),
        ("Return and Deletion",
         "On Controller's choice, Processor shall return or delete all Controller Personal Data within sixty "
         "(60) days after the end of the services."),
        ("Liability",
         "The liability cap and exclusions of the Master Agreement apply to this DPA; each Party's aggregate "
         "liability under the Master Agreement and this DPA shall not exceed the fees paid in the twenty-four "
         "(24) months preceding the claim."),
        ("Governing Law",
         "This DPA is governed by the laws of Denmark, without prejudice to mandatory GDPR provisions."),
    ],
))

C.append(dict(
    file="21_sponsorship_agreement_high_risk",
    title="Event Sponsorship Agreement",
    party_a="Cascadia Marathon Organizing Committee (Organizer)",
    party_b="Ironpeak Energy Ltd. (Sponsor)",
    preamble=("This Event Sponsorship Agreement (the \"Agreement\") is entered into as of November 11, 2026 (the "
              "\"Effective Date\"), between the Cascadia Marathon Organizing Committee, an Oregon nonprofit "
              "corporation (\"Organizer\"), and Ironpeak Energy Ltd., a British Columbia corporation (\"Sponsor\"), "
              "for sponsorship of the 2027 Cascadia Marathon Festival taking place June 12-13, 2027 (the "
              "\"Event\"). Rights granted under this Agreement run through the post-Event wrap-up period ending "
              "August 31, 2027."),
    sections=[
        ("Sponsorship Package",
         "Sponsor purchases the Title Sponsor package described in Exhibit A, including naming rights (\"Cascadia "
         "Marathon presented by Ironpeak Energy\"), the finish-line festival booth, thirty (30) VIP registrations, "
         "and logo placement on all event merchandise."),
        ("Category Exclusivity",
         "Organizer grants Sponsor exclusive sponsorship rights in the energy and utilities category, and "
         "Organizer shall not accept sponsorship from, or feature branding of, any energy, utility or fuel-"
         "retail brand in the Category during the Term."),
        ("Sponsor's Non-Compete",
         "Sponsor shall not sponsor, or provide material support to, any other running event within Oregon or "
         "Washington with more than 5,000 participants occurring within ninety (90) days of the Event."),
        ("Fee and Payment",
         "Sponsor shall pay a sponsorship fee of $275,000: fifty percent (50%) within fifteen (15) days of the "
         "Effective Date and the balance by March 31, 2027. Fees are non-refundable except as expressly provided "
         "in Section 8."),
        ("Term and Renewal",
         "This Agreement covers the 2027 Event only. It automatically renews for the 2028 Event on the same "
         "terms with a five percent (5%) fee increase unless either Party gives written notice of non-renewal by "
         "October 31, 2027."),
        ("Assignment",
         "Neither Party may assign this Agreement or any of its rights hereunder (including the naming rights) "
         "without the other Party's prior written consent."),
        ("Termination",
         "Once the Event is within ninety (90) days, neither Party may terminate for convenience; earlier "
         "termination for convenience requires ninety (90) days' notice and forfeiture of amounts already paid "
         "if Organizer terminates, or of the first installment if Sponsor terminates."),
        ("Force Majeure and Rescheduling",
         "If the Event is cancelled or rescheduled for reasons beyond Organizer's control, the Event rights "
         "transfer to the rescheduled date, or if no new date is set within twelve (12) months, Organizer shall "
         "refund fifty percent (50%) of amounts paid."),
        ("Limitation of Liability",
         "Organizer's aggregate liability arising out of this Agreement shall not exceed the sponsorship fee "
         "actually received."),
        ("Governing Law",
         "This Agreement is governed by the laws of the State of Oregon; venue lies in Lane County."),
    ],
))

C.append(dict(
    file="22_logistics_services_agreement_medium_risk",
    title="Logistics and Warehousing Services Agreement",
    party_a="Pallasine HomeGoods SA (Shipper)",
    party_b="Meridian Fulfillment Corp. (Provider)",
    preamble=("This Logistics and Warehousing Services Agreement (the \"Agreement\") is entered into as of "
              "January 29, 2026 (the \"Effective Date\"), between Pallasine HomeGoods SA, a Belgian company "
              "(\"Shipper\"), and Meridian Fulfillment Corp., a New Jersey corporation (\"Provider\"), for "
              "warehousing, pick-pack and last-mile tendering services for Shipper's e-commerce orders in the "
              "northeastern United States. The initial term is three (3) years, ending January 28, 2029."),
    sections=[
        ("Services and Service Levels",
         "Provider shall receive, store, pick, pack and tender Shipper's products per the Key Performance "
         "Indicators in Schedule 1 (99.2% inventory accuracy; same-day dispatch for orders placed before 14:00 "
         "ET), measured monthly."),
        ("Storage and Handling",
         "Title to goods remains with Shipper. Provider shall maintain the warehouse conditions specified in "
         "Schedule 2 and keep goods segregated by SKU with lot-level traceability."),
        ("License to Systems Interface",
         "Provider grants Shipper a non-exclusive, non-transferable right during the Term to access Provider's "
         "order-management portal and API solely for Shipper's own order data."),
        ("Term and Renewal",
         "This Agreement automatically renews for successive one (1) year renewal terms unless either Party "
         "gives written notice of non-renewal at least one hundred twenty (120) days before the end of the "
         "then-current term."),
        ("Rates and Volume",
         "Rates per Schedule 3 hold for the initial term; volumes below 60% of the committed forecast in two "
         "consecutive quarters permit Provider to renegotiate storage rates on sixty (60) days' notice."),
        ("Assignment",
         "Neither Party may assign this Agreement without the other's prior written consent, except to an "
         "affiliate or in connection with a merger or sale of substantially all relevant assets upon notice."),
        ("Termination",
         "Either Party may terminate for uncured material breach on thirty (30) days' notice; Provider may "
         "terminate for convenience on one hundred eighty (180) days' notice with a wind-down fee equal to one "
         "month's average monthly billing; Shipper has no convenience termination right during the initial term "
         "but may terminate for consecutive KPI misses per Schedule 1."),
        ("Audit and Inventory Checks",
         "Shipper may audit Provider's inventory records, processes and facilities twice per contract year on "
         "ten (10) business days' notice."),
        ("Insurance",
         "Provider shall maintain warehouseman's legal liability insurance of $10,000,000 in the aggregate, "
         "commercial general liability insurance of $2,000,000 per occurrence, and workers' compensation as "
         "required by law."),
        ("Limitation of Liability",
         "Provider's aggregate liability for loss or damage to goods shall not exceed the lesser of replacement "
         "cost or $150 per shipment, except for losses caused by Provider's gross negligence."),
        ("Governing Law",
         "This Agreement is governed by the laws of the State of New Jersey; venue lies in Hudson County."),
    ],
))

# ---------------------------------------------------------------- main
if __name__ == "__main__":
    made = []
    for spec in C:
        made.append(build_docx(spec))
    # a few PDF versions so PDF parsing can be demoed too
    for idx in (6, 8, 0, 12, 20):  # employment, distribution, saas, JV, sponsorship
        made.append(build_pdf(C[idx]))
    print(f"Generated {len(made)} files in {OUT}:")
    for p in sorted(made):
        print(f"  {p.name}  ({p.stat().st_size/1024:.0f} KB)")
