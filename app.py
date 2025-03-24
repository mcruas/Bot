import streamlit as st
import pandas as pd
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from io import BytesIO
from urllib.parse import urlparse, parse_qs

# Load data
def load_data():
    symptoms = pd.read_csv('data/symptoms.csv')
    tests = pd.read_csv('data/tests.csv')
    exercises = pd.read_csv('data/exercises.csv')
    return symptoms, tests, exercises

def generate_pdf(test_results, conditions, recommended_exercises):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title and Description
    title_style = styles['Title']
    title_style.alignment = 1  # Center alignment
    elements.append(Paragraph("Rehabilitation Assistant Report", title_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("This report provides a summary of your rehabilitation assessment, including failed tests, diagnostic conclusions, and recommended exercises.", styles['Normal']))
    elements.append(Spacer(1, 24))
    
    # Failed Tests Section
    elements.append(Paragraph("Failed Tests", styles['Heading2']))
    elements.append(Spacer(1, 12))
    failed_tests = [test_name for test_name, failed in test_results.items() if failed]
    if failed_tests:
        for test in failed_tests:
            elements.append(Paragraph(f"- {test}", styles['Normal']))
    else:
        elements.append(Paragraph("No tests were failed.", styles['Normal']))
    elements.append(Spacer(1, 24))
    
    # Diagnostic Section
    elements.append(Paragraph("Diagnostic", styles['Heading2']))
    elements.append(Spacer(1, 12))
    if conditions:
        for condition in conditions:
            elements.append(Paragraph(f"- {condition.replace('_', ' ').capitalize()}", styles['Normal']))
    else:
        elements.append(Paragraph("No specific conditions identified.", styles['Normal']))
    elements.append(Spacer(1, 24))
    
    # Training Advice Section
    elements.append(Paragraph("Training Advice", styles['Heading2']))
    elements.append(Spacer(1, 12))
    if not recommended_exercises.empty:
        # Create a table for exercises
        table_data = [["Exercise", "Description", "Sets x Reps", "Frequency"]]
        for _, exercise in recommended_exercises.iterrows():
            table_data.append([
                exercise['exercise_name'],
                exercise['description'],
                f"{exercise['sets']}x{exercise['reps']}",
                exercise['frequency']
            ])
        
        table = Table(table_data, colWidths=[100, 200, 80, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("No exercises recommended.", styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

def main():
    st.title('Rehabilitation Assistant')
    
    # Load data
    symptoms, tests, exercises = load_data()
    
    # Parse URL parameters
    query_params = st.experimental_get_query_params()
    test_mode = query_params.get('test_mode', [''])[0] == 'true'
    
    # Step 1: Body Part Selection
    st.header('Step 1: Identify Your Pain Location')
    body_parts = symptoms['symptom_name'].unique()
    
    # Get default body part from URL or use the first one
    default_body_part = query_params.get('body_part', [body_parts[0]])[0]
    
    # Ensure the default body part is valid
    if default_body_part not in body_parts:
        st.warning(f"Invalid body part '{default_body_part}' specified in URL. Defaulting to '{body_parts[0]}'.")
        default_body_part = body_parts[0]
    
    selected_body_part = st.selectbox(
        'Which part of your body is experiencing pain?',
        body_parts,
        index=body_parts.tolist().index(default_body_part)
    )
    
    if selected_body_part:
        # Get symptom_id
        symptom_id = symptoms[symptoms['symptom_name'] == selected_body_part]['symptom_id'].iloc[0]
        
        # Step 2: Show relevant tests
        st.header('Step 2: Perform Physical Tests')
        st.write('Please perform these tests carefully. Stop if you experience severe pain.')
        
        relevant_tests = tests[tests['symptom_id'] == symptom_id]
        
        # Get failed test IDs from URL
        failed_test_ids = query_params.get('failed_tests', [])
        
        test_results = {}
        for _, test in relevant_tests.iterrows():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                st.write(test['test_name'])
            with col2:
                st.write(test['description'])
            with col3:
                default_checked = str(test['test_id']) in failed_test_ids
                test_results[test['test_name']] = st.checkbox('Pain', key=test['test_name'], value=default_checked)
        
        # Step 3: Diagnostic and Exercise Plan
        if st.button('Get Diagnostic and Generate Exercise Plan') or test_mode:
            st.header('Diagnostic')
            
            # Find conditions based on positive tests
            conditions = set()
            for _, test in relevant_tests.iterrows():
                if test_results[test['test_name']]:
                    conditions.add(test['positive_indication'])
            
            if conditions:
                st.write('Based on your symptoms, you may have the following conditions:')
                for condition in conditions:
                    st.write(f"- {condition.replace('_', ' ').capitalize()}")
                
                st.header('Your Rehabilitation Plan')
                st.write('Here are the recommended exercises:')
                
                # Get exercises for identified conditions
                recommended_exercises = exercises[exercises['condition'].isin(conditions)]
                
                # Prepare data for display
                exercise_data = []
                for _, exercise in recommended_exercises.iterrows():
                    image_path = f"pictures/{exercise['image']}" if exercise['image'] else None
                    image_html = f'<img src="{image_path}" style="height:100px;">' if image_path and os.path.exists(image_path) else ''
                    exercise_data.append({
                        "Name": exercise['exercise_name'],
                        "Description": exercise['description'],
                        "Sets x Reps": f"{exercise['sets']}x{exercise['reps']}",
                        "Frequency": exercise['frequency'],
                        "Image": image_html
                    })
                
                # Convert to DataFrame and generate HTML with left-aligned headers
                df = pd.DataFrame(exercise_data)
                html_table = df.to_html(escape=False, index=False)
                html_table = html_table.replace('<th>', '<th style="text-align: left;">')
                
                # Display exercises in a table
                st.write(html_table, unsafe_allow_html=True)
                
                # Generate PDF
                pdf_buffer = generate_pdf(test_results, conditions, recommended_exercises)
                st.download_button(
                    label="Download Report as PDF",
                    data=pdf_buffer,
                    file_name="rehabilitation_report.pdf",
                    mime="application/pdf"
                )
            else:
                st.write('No specific conditions identified. Please consult a healthcare professional.')

if __name__ == '__main__':
    main() 



# streamlit run app.py