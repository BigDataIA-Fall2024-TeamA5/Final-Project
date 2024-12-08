import streamlit as st

# Define available pages
PAGES = {
    "info": {
        "module": "info",
        "title": "Welcome to Paddock Pal",
        "icon": ":house:",
    },
    "paddockpal": {
        "module": "paddockpal",
        "title": "Paddock Pal Bot",
        "icon": ":robot:",
    }
}

def run():
    # Initialize session state to track the current page
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 'info'

    # Set up a simple sidebar for page navigation
    st.sidebar.title("Navigation")
    for page_key, page_data in PAGES.items():
        if st.sidebar.button(f"{page_data['title']} {page_data['icon']}"):
            st.session_state['current_page'] = page_key

    # Load the page based on session state
    current_page = st.session_state['current_page']
    st.title(PAGES[current_page]["title"])

    # Import and show the page's content
    if current_page == "info":
        import info
        info.show_info()
    elif current_page == "paddockpal":
        import paddockpal
        paddockpal.show_paddockpal()