import streamlit as st
import Streamlit.informationpage as informationpage
import Streamlit.paddockpal1 as paddockpal1
import Streamlit.tracks_drivers as tracks_drivers  # Import the new page

# Define available pages
PAGES = {
    "informationpage": {
        "module": "informationpage",
        "title": "Welcome to Paddock Pal",
        "icon": "🏠",
    },
    "paddockpal1": {
        "module": "paddockpal1",
        "title": "Paddock Pal Bot",
        "icon": "🤖",
    },
    "tracks_drivers": {
        "module": "tracks_drivers",
        "title": "Drivers and Tracks",
        "icon": "🏎️",
    },
}

def run():
    # Initialize session state to track the current page
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 'informationpage'

    # Sidebar navigation
    st.sidebar.title("Navigation")
    for page_key, page_data in PAGES.items():
        if st.sidebar.button(f"{page_data['icon']} {page_data['title']}"):
            st.session_state['current_page'] = page_key

    # Load the selected page
    current_page = st.session_state['current_page']
    st.title(PAGES[current_page]["title"])

    # Render the selected page
    if current_page == "informationpage":
        informationpage.show_info()
    elif current_page == "paddockpal1":
        paddockpal1.show_paddockpal()
    elif current_page == "tracks_drivers":
        tracks_drivers.show_drivers_tracks()

if __name__ == "__main__":
    run()
