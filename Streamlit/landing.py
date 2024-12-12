import streamlit as st
import Streamlit.informationpage as informationpage
import Streamlit.paddockpal as paddockpal1
# Define available pages
PAGES = {
    "informationpage": {
        "module": "informationpage",
        "title": "Welcome to Paddock Pal",
        "icon": ":house:",
    },
    "paddockpal1": {
        "module": "paddockpal1",
        "title": "Paddock Pal Bot",
        "icon": ":robot:",
    }
}

def run():
    # Initialize session state to track the current page
    st.title("PLEASE OPEN")
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 'informationpage'

    # Set up a simple sidebar for page navigation
    st.sidebar.title("Navigation")
    for page_key, page_data in PAGES.items():
        if st.sidebar.button(f"{page_data['title']} {page_data['icon']}"):
            st.session_state['current_page'] = page_key

    # Load the page based on session state
    current_page = st.session_state['current_page']
    st.title(PAGES[current_page]["title"])

    # Import and show the page's content
    if current_page == "informationpage":
        informationpage.show_info()
    elif current_page == "paddockpal1":
        paddockpal1.show_paddockpal()