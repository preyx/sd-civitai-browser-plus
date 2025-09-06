import fnmatch
import json
import os
import re
import gradio as gr

# ===  WebUI imports ===
from modules import script_callbacks, shared
from modules.shared import opts, cmd_opts
from modules.paths import extensions_dir
from modules.options import categories

# === Extension imports ===
import scripts.civitai_download as _download
import scripts.civitai_file_manage as _file
import scripts.civitai_global as gl
import scripts.civitai_api as _api
from scripts.civitai_global import print, debug_print


gl.init()


def saveSettings(ust, ct, pt, st, bf, cj, ol, hi, sn, ss, ts):
    config = cmd_opts.ui_config_file

    # Create a dictionary to map the settings to their respective variables
    settings_map = {
        'civitai_interface/Search type:/value': ust,
        'civitai_interface/Content type:/value': ct,
        'civitai_interface/Time period:/value': pt,
        'civitai_interface/Sort by:/value': st,
        'civitai_interface/Base model:/value': bf,
        'civitai_interface/Save info after download/value': cj,
        'civitai_interface/Divide cards by date/value': False,  # This is a toggle, so its state does not matter here
        'civitai_interface/Liked models only/value': ol,
        'civitai_interface/Hide installed models/value': hi,
        'civitai_interface/NSFW content/value': sn,
        'civitai_interface/Tile size:/value': ss,
        'civitai_interface/Tile count:/value': ts
    }

    # Load the current contents of the config file into a dictionary
    try:
        with open(config, 'r', encoding='utf8') as file:
            data = json.load(file)
    except:
        print(f"Cannot save settings, failed to open '{file}'")
        print('Please try to manually repair the file or remove it to reset settings.')
        return

    # Remove any keys containing the text `civitai_interface`
    keys_to_remove = [key for key in data if 'civitai_interface' in key]
    for key in keys_to_remove:
        del data[key]

    # Update the dictionary with the new settings
    data.update(settings_map)

    # Save the modified content back to the file
    with open(config, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)
        print(f"Updated settings to: {config}")

# === ANXETY EDITs ===
def all_visible(html_check):
    # Count the number of model-checkbox occurrences in the HTML
    checkbox_count = html_check.count('model-checkbox')
    # Show the button only if there are 2 or more checkboxes (more than 1 model to select)
    return gr.Button.update(visible=checkbox_count >= 2)

def HTMLChange(input):
    return gr.HTML.update(value=input)

def show_multi_buttons(model_list, type_list, version_value):
    model_list = json.loads(model_list)
    type_list = json.loads(type_list)
    otherButtons = True
    multi_file_subfolder = False
    default_subfolder = 'Only available if the selected files are of the same model type'
    sub_folders = ['None']
    BtnDwn = version_value and not version_value.endswith('[Installed]') and not model_list
    BtnDel = version_value.endswith('[Installed]')

    dot_subfolders = getattr(opts, 'dot_subfolders', True)

    multi = bool(model_list) and not len(gl.download_queue) > 0
    if model_list:
        otherButtons = False
    if type_list and all(x == type_list[0] for x in type_list):
        multi_file_subfolder = True
        model_folder = os.path.join(_api.contenttype_folder(type_list[0]))
        default_subfolder = 'None'
        try:
            for root, dirs, _ in os.walk(model_folder, followlinks=True):
                if dot_subfolders:
                    dirs = [d for d in dirs if not d.startswith('.')]
                    dirs = [d for d in dirs if not any(part.startswith('.') for part in os.path.join(root, d).split(os.sep))]
                for d in dirs:
                    sub_folder = os.path.relpath(os.path.join(root, d), model_folder)
                    if sub_folder:
                        sub_folders.append(f'{os.sep}{sub_folder}')
            sub_folders.remove('None')
            sub_folders = sorted(sub_folders, key=lambda x: (x.lower(), x))
            sub_folders.insert(0, 'None')

            list = set()
            sub_folders = [x for x in sub_folders if not (x in list or list.add(x))]
        except:
            sub_folders = ['None']

    return (gr.Button.update(visible=multi, interactive=multi), # Download Multi Button
            gr.Button.update(visible=BtnDwn if multi else True if not version_value.endswith('[Installed]') else False), # Download Button
            gr.Button.update(visible=BtnDel if not model_list else False), # Delete Button
            gr.Button.update(visible=otherButtons), # Save model info Button
            gr.Button.update(visible=otherButtons), # Save images Button
            gr.Dropdown.update(visible=multi, interactive=multi_file_subfolder, choices=sub_folders, value=default_subfolder) # Selected type sub folder
            )

def txt2img_output(image_url):
    clean_url = image_url[4:]
    geninfo = _api.fetch_and_process_image(clean_url)
    if geninfo:
        nr = _download.random_number()
        geninfo = nr + geninfo
        return gr.Textbox.update(value=geninfo)

## === ANXETY EDITs ===
def get_base_models():
    api_url = 'https://civitai.com/api/v1/models?baseModels=GetModels'
    json_return = _api.request_civit_api(api_url, True)
    # The data below is taken from the API response
    default_options = [
        'SD 1.4',
        'SD 1.5',
        'SD 1.5 LCM',
        'SD 1.5 Hyper',
        'SD 2.0',
        'SD 2.0 768',
        'SD 2.1',
        'SD 2.1 768',
        'SD 2.1 Unclip',
        'SDXL 0.9',
        'SDXL 1.0',
        'SD 3',
        'SD 3.5',
        'SD 3.5 Medium',
        'SD 3.5 Large',
        'SD 3.5 Large Turbo',
        'Pony',
        'Flux.1 S',
        'Flux.1 D',
        'Flux.1 Kontext',
        'AuraFlow',
        'SDXL 1.0 LCM',
        'SDXL Distilled',
        'SDXL Turbo',
        'SDXL Lightning',
        'SDXL Hyper',
        'SVD',
        'SVD XT',
        'Playground v2',
        'PixArt a',
        'PixArt E',
        'Hunyuan 1',
        'Hunyuan Video',
        'Illustrious',
        'LTXV',
        'NoobAI',
        'Wan Video',
        'Other'
    ]

    if not isinstance(json_return, dict):
        print("Couldn't fetch latest baseModel options, using default.")
        return default_options

    try:
        options = json.loads(json_return['error']['message'])[0]['errors'][0][0]['values']
        return options
    except (KeyError, IndexError) as e:
        print(f"Basemodel fetch error extracting options: {e}")
        return default_options

## === ANXETY EDITs ===
def on_ui_tabs():
    page_header = getattr(opts, 'page_header', False)
    lobe_directory = None

    for root, dirs, files in os.walk(extensions_dir, followlinks=True):
        for dir_name in fnmatch.filter(dirs, '*lobe*'):
            lobe_directory = os.path.join(root, dir_name)
            break

    # Different ID's for Lobe Theme
    component_id = 'togglesL' if lobe_directory else 'toggles'
    toggle1 = 'toggle1L' if lobe_directory else 'toggle1'
    toggle2 = 'toggle2L' if lobe_directory else 'toggle2'
    toggle3 = 'toggle3L' if lobe_directory else 'toggle3'
    toggle5 = 'toggle5L' if lobe_directory else 'toggle5'
    refreshbtn = 'refreshBtnL' if lobe_directory else 'refreshBtn'
    filterBox = 'filterBoxL' if lobe_directory else 'filterBox'

    if page_header:
        header = 'headerL' if lobe_directory else 'header'
    else:
        header = 'header_off'

    api_key = getattr(opts, 'custom_api_key', '')
    if api_key:
        toggle4 = 'toggle4L_api' if lobe_directory else 'toggle4_api'
        show_only_liked = True
    else:
        toggle4 = 'toggle4L' if lobe_directory else 'toggle4'
        show_only_liked = False

    content_choices = _file.get_content_choices()
    scan_choices = _file.get_content_choices(scan_choices=True)

    with gr.Blocks() as civitai_interface:
        # Browser Tab
        with gr.Tab(label='Browser', elem_id='browserTab'):
            with gr.Row(elem_id='searchRow'):
                with gr.Accordion(label='', open=False, elem_id=filterBox):
                    with gr.Row():
                        use_search_term = gr.Radio(label='Search type:', choices=['Model name', 'User name', 'Tag', 'SHA256'], value='Model name', elem_id='searchType')
                    with gr.Row():
                        content_type = gr.Dropdown(label='Content type:', choices=content_choices, value=None, type='value', multiselect=True, elem_id='centerText')
                    with gr.Row():
                        base_filter = gr.Dropdown(label='Base model:', multiselect=True, choices=get_base_models(), value=None, type='value', elem_id='centerText')
                    with gr.Row():
                        period_type = gr.Dropdown(label='Time period:', choices=['All Time', 'Year', 'Month', 'Week', 'Day'], value='Month', type='value', elem_id='centerText')
                        sort_type = gr.Dropdown(label='Sort by:', choices=['Newest','Oldest','Most Downloaded','Highest Rated','Most Liked','Most Buzz','Most Discussed','Most Collected','Most Images'], value='Highest Rated', type='value', elem_id='centerText')
                    with gr.Row(elem_id=component_id):
                        create_json = gr.Checkbox(label=f"Save info after download", value=True, elem_id=toggle1, min_width=171)
                        show_nsfw = gr.Checkbox(label='NSFW content', value=False, elem_id=toggle2, min_width=107)
                        toggle_date = gr.Checkbox(label='Divide cards by date', value=False, elem_id=toggle3, min_width=142)
                        only_liked = gr.Checkbox(label='Liked models only', value=False, interactive=show_only_liked, elem_id=toggle4, min_width=163)
                        hide_installed = gr.Checkbox(label='Hide installed models', value=False, elem_id=toggle5, min_width=170)
                    with gr.Row():
                        size_slider = gr.Slider(label='Tile size:', minimum=8, maximum=20, value=12, step=0.25)
                        tile_count_slider = gr.Slider(label='Tile count:', minimum=1, maximum=100, value=27, step=1)
                    with gr.Row(elem_id='save_set_box'):
                        save_settings = gr.Button(value='Save settings as default', elem_id='save_set_btn')
                search_term = gr.Textbox(label='', placeholder='Enter model name, or paste a CivitAI link', elem_id='searchBox')
                refresh = gr.Button(value='', elem_id=refreshbtn, icon='placeholder')
            with gr.Row(elem_id=header):
                with gr.Row(elem_id='pageBox'):
                    get_prev_page = gr.Button(value='Prev page', interactive=False, elem_id='pageBtn1')
                    page_slider = gr.Slider(label='Current page:', step=1, minimum=1, maximum=1, min_width=80, elem_id='pageSlider')
                    get_next_page = gr.Button(value='Next page', interactive=False, elem_id='pageBtn2')
                with gr.Row(elem_id='pageBoxMobile'):
                    pass # Row used for button placement on mobile
            with gr.Row(elem_id='select_all_models_container'):
                select_all = gr.Button(value='Select All', elem_id='select_all_models', visible=False)
            with gr.Row():
                list_html = gr.HTML(value='<div style="font-size: 24px; text-align: center; margin: 50px;">Click the search icon to load models.<br>Use the filter icon to filter results.</div>')
            with gr.Row():
                download_progress = gr.HTML(value='<div style="min-height: 0px;"></div>', elem_id='DownloadProgress')
            with gr.Row():
                list_models = gr.Dropdown(label='Model:', choices=[], interactive=False, elem_id='quicksettings1', value=None)
                list_versions = gr.Dropdown(label='Version:', choices=[], interactive=False, elem_id='quicksettings0', value=None)
                file_list = gr.Dropdown(label='File:', choices=[], interactive=False, elem_id='file_list', value=None)
            with gr.Row():
                with gr.Column(scale=4):
                    install_path = gr.Textbox(label='Download folder:', interactive=False, max_lines=1)
                with gr.Column(scale=2):
                    sub_folder = gr.Dropdown(label='Sub folder:', choices=[], interactive=False, value=None)
            with gr.Row():
                with gr.Column(scale=4):
                    trained_tags = gr.Textbox(label='Trained tags (if any):', value=None, interactive=False, lines=1)
                with gr.Column(scale=2, elem_id='spanWidth'):
                    base_model = gr.Textbox(label='Base model: ', value=None, interactive=False, lines=1, elem_id='baseMdl')
                    model_filename = gr.Textbox(label='Model filename:', interactive=False, value=None)
            with gr.Row():
                save_info = gr.Button(value='Save model info', interactive=False)
                save_images = gr.Button(value='Save images', interactive=False)
                delete_model = gr.Button(value='Delete model', interactive=False, visible=False)
                download_model = gr.Button(value='Download model', interactive=False)
                subfolder_selected = gr.Dropdown(label='Sub folder for selected files:', choices=[], interactive=False, visible=False, value=None, allow_custom_value=True)
                download_selected = gr.Button(value='Download all selected', interactive=False, visible=False, elem_id='download_all_button')
            with gr.Row():
                cancel_all_model = gr.Button(value='Cancel all downloads', interactive=False, visible=False)
                cancel_model = gr.Button(value='Cancel current download', interactive=False, visible=False)
            with gr.Row():
                preview_html = gr.HTML(elem_id='civitai_preview_html')
            with gr.Row(elem_id='backToTopContainer'):
                back_to_top = gr.Button(value='↑', elem_id='backToTop')

        # Update Tab
        with gr.Tab(label='Update Models', elem_id='updateTab'):
            with gr.Row():
                selected_tags = gr.CheckboxGroup(elem_id='selected_tags', label='Selected content types:', choices=scan_choices, value=['All'])
            with gr.Row(elem_id='civitai_update_toggles'):
                overwrite_toggle = gr.Checkbox(elem_id='overwrite_toggle', label='Overwrite any existing files. (previews, HTMLs, tags, descriptions)', value=True, min_width=300)
                skip_hash_toggle = gr.Checkbox(elem_id='skip_hash_toggle', label='One-Time Hash Generation for externally downloaded models.', value=True, min_width=300)
                do_html_gen = gr.Checkbox(elem_id='do_html_gen', label='Save HTML file for each model when updating info & tags (increases process time).', value=False, min_width=300)
            with gr.Row():
                save_all_tags = gr.Button(value='Update model info & tags', interactive=True, visible=True)
                cancel_all_tags = gr.Button(value='Cancel updating model info & tags', interactive=False, visible=False)
            with gr.Row():
                tag_progress = gr.HTML(value='<div style="min-height: 0px;"></div>')
            with gr.Row():
                update_preview = gr.Button(value='Update model preview', interactive=True, visible=True)
                cancel_update_preview = gr.Button(value='Cancel updating model previews', interactive=False, visible=False)
            with gr.Row():
                preview_progress = gr.HTML(value='<div style="min-height: 0px;"></div>')
            with gr.Row():
                ver_search = gr.Button(value='Scan for available updates', interactive=True, visible=True)
                cancel_ver_search = gr.Button(value='Cancel updates scan', interactive=False, visible=False)
                load_to_browser = gr.Button(value='Load outdated models to browser', interactive=False, visible=False)
            with gr.Row():
                version_progress = gr.HTML(value='<div style="min-height: 0px;"></div>')
            with gr.Row():
                load_installed = gr.Button(value='Load all installed models', interactive=True, visible=True)
                cancel_installed = gr.Button(value='Cancel loading models', interactive=False, visible=False)
                load_to_browser_installed = gr.Button(value='Load installed models to browser', interactive=False, visible=False)
            with gr.Row():
                installed_progress = gr.HTML(value='<div style="min-height: 0px;"></div>')
            with gr.Row():
                organize_models = gr.Button(value='Organize model files', interactive=True, visible=False) # Organize models hidden until implemented
                cancel_organize = gr.Button(value='Cancel loading models', interactive=False, visible=False)
            with gr.Row():
                organize_progress = gr.HTML(value='<div style="min-height: 0px;"></div>')

        # Queue Tab
        with gr.Tab(label='Download Queue', elem_id='queueTab'):

            def get_style(size, left_border):
                return f"flex-grow: {size};" + ('border-left: 1px solid var(--border-color-primary);' if left_border else '') + 'border-bottom: 1px solid var(--border-color-primary);padding: 5px 10px 5px 10px;width: 0;'

            download_manager_html = gr.HTML(elem_id='civitai_dl_list', value=f'''
                <div style="display: flex;font-size: var(--section-header-text-size);border: 1px solid transparent;">
                <div style="{get_style(1, False)}"><span>Model:</span></div>
                <div style="{get_style(0.75, True)}"><span>Version:</span></div>
                <div style="{get_style(1.5, True)}"><span>Path:</span></div>
                <div style="{get_style(1.5, True)}"><span>Status:</span></div>
                <div style="{get_style(0.3, True)}"><span>Action:</span></div>
                </div>
                <div class="civitai_nonqueue_list">
                </div>
                <span style="padding: 10px 0px 5px 5px;font-size: larger;border-bottom: 1px solid var(--border-color-primary);">In queue: (drag items to rearrange queue order)</span>
                <div class="list" id="queue_list">
                </div>
                ''')

        def format_custom_subfolders():
            separator = '␞␞'
            with open(gl.subfolder_json, 'r') as f:
                data = json.load(f)
            # Filter out timestamp and non-string values
            filtered_data = {key: value for key, value in data.items()
                           if key != "created_at" and isinstance(value, str)}
            result = separator.join([f"{key}{separator}{value}" for key, value in filtered_data.items()])
            return result

        #Invisible triggers/variables
        #Yes, there is probably a much better way of passing variables/triggering functions between javascript and python

        gr.Textbox(elem_id='custom_subfolders_list', visible=False, value=format_custom_subfolders())
        model_id = gr.Textbox(visible=False)
        queue_trigger = gr.Textbox(visible=False)
        dl_url = gr.Textbox(visible=False)
        civitai_text2img_output = gr.Textbox(visible=False)
        civitai_text2img_input = gr.Textbox(elem_id='civitai_text2img_input', visible=False)
        page_slider_trigger = gr.Textbox(elem_id='page_slider_trigger', visible=False)
        selected_model_list = gr.Textbox(elem_id='selected_model_list', visible=False)
        selected_type_list = gr.Textbox(elem_id='selected_type_list', visible=False)
        html_cancel_input = gr.Textbox(elem_id='html_cancel_input', visible=False)
        queue_html_input = gr.Textbox(elem_id='queue_html_input', visible=False)
        list_html_input = gr.Textbox(elem_id='list_html_input', visible=False)
        preview_html_input = gr.Textbox(elem_id='preview_html_input', visible=False)
        create_subfolder = gr.Textbox(elem_id='create_subfolder', visible=False)
        send_to_browser = gr.Textbox(elem_id='send_to_browser', visible=False)
        arrange_dl_id = gr.Textbox(elem_id='arrange_dl_id', visible=False)
        remove_dl_id = gr.Textbox(elem_id='remove_dl_id', visible=False)
        model_select = gr.Textbox(elem_id='model_select', visible=False)
        model_sent = gr.Textbox(elem_id='model_sent', visible=False)
        type_sent = gr.Textbox(elem_id='type_sent', visible=False)
        click_first_item = gr.Textbox(visible=False)
        empty = gr.Textbox(value='', visible=False)
        download_start = gr.Textbox(visible=False)
        download_finish = gr.Textbox(visible=False)
        tag_start = gr.Textbox(visible=False)
        tag_finish = gr.Textbox(visible=False)
        preview_start = gr.Textbox(visible=False)
        preview_finish = gr.Textbox(visible=False)
        ver_start = gr.Textbox(visible=False)
        ver_finish = gr.Textbox(visible=False)
        installed_start = gr.Textbox(visible=None)
        installed_finish = gr.Textbox(visible=None)
        organize_start = gr.Textbox(visible=None)
        organize_finish = gr.Textbox(visible=None)
        delete_finish = gr.Textbox(visible=False)
        current_model = gr.Textbox(visible=False)
        current_sha256 = gr.Textbox(visible=False)
        model_preview_html_input = gr.Textbox(visible=False)

        def ToggleDate(toggle_date):
            gl.sortNewest = toggle_date

        def select_subfolder(sub_folder):
            if sub_folder == 'None' or sub_folder == 'Only available if the selected files are of the same model type':
                newpath = gl.main_folder
            else:
                newpath = str(gl.main_folder) + sub_folder
            return gr.Textbox.update(value=newpath)

        # Javascript Functions #

        list_html_input.change(fn=None, inputs=hide_installed, _js='(toggleValue) => hideInstalled(toggleValue)')
        hide_installed.input(fn=None, inputs=hide_installed, _js='(toggleValue) => hideInstalled(toggleValue)')

        civitai_text2img_output.change(fn=None, inputs=civitai_text2img_output, _js='(genInfo) => genInfo_to_txt2img(genInfo)')

        download_selected.click(fn=None, _js='() => deselectAllModels()')

        select_all.click(fn=None, _js='() => selectAllModels()')

        list_models.select(fn=None, inputs=list_models, _js='(list_models) => select_model(list_models)')

        preview_html_input.change(fn=None, _js='() => adjustFilterBoxAndButtons()')
        preview_html_input.change(fn=None, _js='() => setDescriptionToggle()')

        back_to_top.click(fn=None, _js='() => BackToTop()')

        page_slider.release(fn=None, _js='() => pressRefresh()')

        card_updates = [queue_trigger, download_finish, delete_finish]
        for func in card_updates:
            func.change(fn=None, inputs=current_model, _js='(modelName) => updateCard(modelName)')

        list_html_input.change(fn=None, inputs=size_slider, _js='(size) => updateCardSize(size, size * 1.5)')
        size_slider.change(fn=None, inputs=size_slider, _js='(size) => updateCardSize(size, size * 1.5)')

        model_preview_html_input.change(fn=None, inputs=model_preview_html_input, _js='(html_input) => inputHTMLPreviewContent(html_input)')

        queue_html_input.change(fn=None, _js='() => setSortable()')

        click_first_item.change(fn=None, _js='() => clickFirstFigureInColumn()')

        # Filter button Functions #

        queue_html_input.change(fn=HTMLChange, inputs=[queue_html_input], outputs=download_manager_html)
        list_html_input.change(fn=HTMLChange, inputs=[list_html_input], outputs=list_html)
        preview_html_input.change(fn=HTMLChange, inputs=[preview_html_input], outputs=preview_html)

        remove_dl_id.change(
            fn=_download.remove_from_queue,
            inputs=[remove_dl_id]
        )

        arrange_dl_id.change(
            fn=_download.arrange_queue,
            inputs=[arrange_dl_id]
        )

        html_cancel_input.change(
            fn=_download.download_cancel
        )

        html_cancel_input.change(fn=None, _js='() => cancelCurrentDl()')

        save_settings.click(
            fn=saveSettings,
            inputs=[
                use_search_term,
                content_type,
                period_type,
                sort_type,
                base_filter,
                create_json,
                only_liked,
                hide_installed,
                show_nsfw,
                size_slider,
                tile_count_slider
            ]
        )

        toggle_date.input(
            fn=ToggleDate,
            inputs=[toggle_date]
        )

        # Model Button Functions #

        civitai_text2img_input.change(fn=txt2img_output,inputs=civitai_text2img_input,outputs=civitai_text2img_output)

        list_html_input.change(fn=all_visible, inputs=list_html_input, outputs=select_all)

        def update_models_dropdown(input):
            # If there is no loaded model data, reset all UI elements and show a message
            if not gl.json_data:
                return (
                    gr.Dropdown.update(value=None, choices=[], interactive=False),  # Model list dropdown
                    gr.Dropdown.update(value=None, choices=[], interactive=False),  # Version list dropdown
                    gr.Textbox.update(value=None),                                  # Preview HTML
                    gr.Textbox.update(value=None, interactive=False),               # Trained tags textbox
                    gr.Textbox.update(value=None, interactive=False),               # Base model textbox
                    gr.Textbox.update(value=None, interactive=False),               # Model filename textbox
                    gr.Textbox.update(value=None, interactive=False),               # Install path textbox
                    gr.Dropdown.update(value=None, choices=[], interactive=False),  # Subfolder dropdown
                    gr.Button.update(interactive=False),                            # Download model button
                    gr.Button.update(interactive=False),                            # Save image button
                    gr.Button.update(interactive=False, visible=False),             # Delete model button
                    gr.Dropdown.update(value=None, choices=[], interactive=False),  # File list dropdown
                    gr.Textbox.update(value=None),                                  # Download URL textbox
                    gr.Textbox.update(value=None),                                  # Model ID textbox
                    gr.Textbox.update(value=None),                                  # Current SHA256 textbox
                    gr.Button.update(interactive=False),                            # Save model info button
                    gr.Textbox.update(
                        value='<div style="font-size: 24px; text-align: center; margin: 50px;">Click the search icon to load models.<br>Use the filter icon to filter results.</div>'
                    )  # Model list HTML message
                )

            model_string = re.sub(r'\.\d{3}$', '', input)
            model_name, model_id = _api.extract_model_info(model_string)
            model_versions = _api.update_model_versions(model_id)

            # Get detailed model info for the selected version
            (
                html,
                tags,
                base_model,
                download_button,
                save_images_button,
                delete_button,
                file_list,
                model_filename,
                download_url,
                model_id_value,
                current_sha256,
                install_path,
                sub_folder
            ) = _api.update_model_info(model_string, model_versions.get('value'))

            # Return all UI updates in the expected order
            return (
                gr.Dropdown.update(value=model_string, interactive=True), # Model dropdown
                model_versions,                                           # Version dropdown
                html,                                                     # Preview HTML
                tags,                                                     # Trained tags
                base_model,                                               # Base model
                model_filename,                                           # Model filename
                install_path,                                             # Install path
                sub_folder,                                               # Sub folder
                download_button,                                          # Download button
                save_images_button,                                       # Save images button
                delete_button,                                            # Delete button
                file_list,                                                # File list
                download_url,                                             # Download URL
                model_id_value,                                           # Model ID
                current_sha256,                                           # Current SHA256
                gr.Button.update(interactive=True),                       # Save model info button
                gr.Textbox.update()                                       # Model list HTML
            )

        model_select.change(
            fn=update_models_dropdown,
            inputs=[model_select],
            outputs=[
                list_models,
                list_versions,
                preview_html,
                trained_tags,
                base_model,
                model_filename,
                install_path,
                sub_folder,
                download_model,
                save_images,
                delete_model,
                file_list,
                dl_url,
                model_id,
                current_sha256,
                save_info,
                list_html_input
            ]
        )

        model_sent.change(
            fn=_file.model_from_sent,
            inputs=[model_sent, type_sent],
            outputs=[model_preview_html_input]
        )

        send_to_browser.change(
            fn=_file.send_to_browser,
            inputs=[send_to_browser, type_sent, click_first_item],
            outputs=[list_html_input, get_prev_page, get_next_page, page_slider, click_first_item]
        )

        sub_folder.select(
            fn=select_subfolder,
            inputs=[sub_folder],
            outputs=[install_path]
        )

        subfolder_selected.select(
            fn=select_subfolder,
            inputs=[subfolder_selected],
            outputs=[install_path]
        )

        list_versions.select(
            fn=_api.update_model_info,
            inputs=[
                list_models,
                list_versions
            ],
            outputs=[
                preview_html_input,
                trained_tags,
                base_model,
                download_model,
                save_images,
                delete_model,
                file_list,
                model_filename,
                dl_url,
                model_id,
                current_sha256,
                install_path,
                sub_folder
            ]
        )

        file_list.input(
            fn=_api.update_file_info,
            inputs=[
                list_models,
                list_versions,
                file_list
            ],
            outputs=[
                model_filename,
                dl_url,
                model_id,
                current_sha256,
                download_model,
                delete_model,
                install_path,
                sub_folder
            ]
        )

        # Download/Save Model Button Functions #

        selected_model_list.change(
            fn=show_multi_buttons,
            inputs=[selected_model_list, selected_type_list, list_versions],
            outputs=[
                download_selected,
                download_model,
                delete_model,
                save_info,
                save_images,
                subfolder_selected
            ]
        )

        download_model.click(
            fn=_download.download_start,
            inputs=[
                download_start,
                dl_url,
                model_filename,
                install_path,
                list_models,
                list_versions,
                current_sha256,
                model_id,
                create_json,
                download_manager_html
            ],
            outputs=[
                download_model,
                cancel_model,
                cancel_all_model,
                download_start,
                download_progress,
                download_manager_html
            ]
        )

        download_selected.click(
            fn=_download.selected_to_queue,
            inputs=[
                selected_model_list,
                subfolder_selected,
                download_start,
                create_json,
                download_manager_html
            ],
            outputs=[
                download_model,
                cancel_model,
                cancel_all_model,
                download_start,
                download_progress,
                download_manager_html
            ]
        )

        for component in [download_start, queue_trigger]:
            component.change(fn=None, _js='() => setDownloadProgressBar()')
            component.change(
                fn=_download.download_create_thread,
                inputs=[download_finish, queue_trigger],
                outputs=[
                    download_progress,
                    current_model,
                    download_finish,
                    queue_trigger
                ]
            )

        download_finish.change(
            fn=_download.download_finish,
            inputs=[
                model_filename,
                list_versions,
                model_id
            ],
            outputs=[
                download_model,
                cancel_model,
                cancel_all_model,
                delete_model,
                download_progress,
                list_versions
            ]
        )

        cancel_model.click(_download.download_cancel)
        cancel_all_model.click(_download.download_cancel_all)

        cancel_model.click(fn=None, _js='() => cancelCurrentDl()')
        cancel_all_model.click(fn=None, _js='() => cancelAllDl()')

        delete_model.click(
            fn=_file.delete_model,
            inputs=[
                delete_finish,
                model_filename,
                list_models,
                list_versions,
                current_sha256,
                selected_model_list
            ],
            outputs=[
                download_model,
                cancel_model,
                delete_model,
                delete_finish,
                current_model,
                list_versions
            ]
        )

        save_info.click(
            fn=_file.save_model_info,
            inputs=[
                install_path,
                model_filename,
                sub_folder,
                current_sha256,
                preview_html_input
            ],
            outputs=[]
        )

        def save_images_wrapper(preview_html, model_filename, install_path, sub_folder, model_id):
            """Wrapper function to save images with API response data"""
            print(f"Save Images Debug: model_id={model_id}, preview_html_length={len(preview_html) if preview_html else 0}")

            # Generate proper HTML with images if preview_html is empty or doesn't contain images
            if not preview_html or 'data-sampleimg="true"' not in preview_html:
                debug_print(f"Generating HTML with images for model {model_id}")
                if model_id:
                    try:
                        # Get model versions for the current model
                        model_versions = _api.update_model_versions(model_id)
                        if model_versions and model_versions.get('value'):
                            # Generate HTML with images using the same function as automatic version
                            result = _api.update_model_info(None, model_versions.get('value'), False, model_id)
                            if isinstance(result, tuple) and len(result) >= 1:
                                preview_html = result[0]  # First element is the HTML
                            else:
                                preview_html = str(result) if result else ""
                            debug_print(f"Generated HTML length: {len(preview_html) if preview_html else 0}")
                    except Exception as e:
                        debug_print(f"Error generating HTML: {e}")

            if model_id and gl.json_data:
                # Find the current model in the API data
                for item in gl.json_data.get('items', []):
                    if int(item.get('id', 0)) == int(model_id):
                        debug_print(f"Using existing API data for model {model_id}")
                        # Ensure preview_html is a string
                        if not isinstance(preview_html, str):
                            preview_html = str(preview_html) if preview_html else ""
                        _file.save_images(preview_html, model_filename, install_path, sub_folder, api_response=gl.json_data)
                        return
                # If model not found in current data, try to fetch it
                try:
                    debug_print(f"Fetching API data for model {model_id}")
                    api_response = _api.request_civit_api(f"https://civitai.com/api/v1/models/{model_id}")
                    # Ensure preview_html is a string
                    if not isinstance(preview_html, str):
                        preview_html = str(preview_html) if preview_html else ""
                    _file.save_images(preview_html, model_filename, install_path, sub_folder, api_response=api_response)
                    return
                except Exception as e:
                    debug_print(f"Error fetching API data: {e}")
            # Fallback to save without API response
            debug_print(f"Using fallback save method")
            # Ensure preview_html is a string
            if not isinstance(preview_html, str):
                preview_html = str(preview_html) if preview_html else ""
            _file.save_images(preview_html, model_filename, install_path, sub_folder)

        save_images.click(
            fn=save_images_wrapper,
            inputs=[
                preview_html_input,
                model_filename,
                install_path,
                sub_folder,
                model_id
            ],
            outputs=[]
        )

        # Common input&output lists #

        page_inputs = [
            content_type,
            sort_type,
            period_type,
            use_search_term,
            search_term,
            page_slider,
            base_filter,
            only_liked,
            show_nsfw,
            tile_count_slider
        ]

        refresh_inputs = [empty if item == page_slider else item for item in page_inputs]

        page_outputs = [
            list_models,
            list_versions,
            list_html_input,
            get_prev_page,
            get_next_page,
            page_slider,
            save_info,
            save_images,
            download_model,
            delete_model,
            install_path,
            sub_folder,
            file_list,
            preview_html_input,
            trained_tags,
            base_model,
            model_filename
        ]

        file_scan_inputs = [
            selected_tags,
            ver_finish,
            tag_finish,
            installed_finish,
            preview_finish,
            overwrite_toggle,
            tile_count_slider,
            skip_hash_toggle,
            do_html_gen
        ]

        load_to_browser_inputs = [
            content_type,
            sort_type,
            period_type,
            use_search_term,
            search_term,
            tile_count_slider,
            base_filter,
            show_nsfw
        ]

        cancel_btn_list = [cancel_all_tags, cancel_ver_search, cancel_installed, cancel_update_preview]

        browser = [ver_search, save_all_tags, load_installed, update_preview]

        browser_installed_load = [cancel_installed, load_to_browser_installed, installed_progress]
        browser_load = [cancel_ver_search, load_to_browser, version_progress]

        browser_installed_list = page_outputs + browser + browser_installed_load
        browser_list = page_outputs + browser + browser_load

        # Page Button Functions #

        page_btn_list = {
            refresh.click: (_api.initial_model_page, True),
            search_term.submit: (_api.initial_model_page, True),
            page_slider_trigger.change: (_api.initial_model_page, False),
            get_next_page.click: (_api.next_model_page, False),
            get_prev_page.click: (_api.prev_model_page, False)
        }

        for trigger, (function, use_refresh_inputs) in page_btn_list.items():
            inputs_to_use = refresh_inputs if use_refresh_inputs else page_inputs
            trigger(fn=function, inputs=inputs_to_use, outputs=page_outputs)
            trigger(fn=None, _js='() => multi_model_select()')

        for button in cancel_btn_list:
            button.click(fn=_file.cancel_scan)

        # Update model Functions #

        ver_search.click(
            fn=_file.ver_search_start,
            inputs=[ver_start],
            outputs=[
                ver_start,
                ver_search,
                cancel_ver_search,
                load_installed,
                save_all_tags,
                update_preview,
                organize_models,
                version_progress
            ]
        )

        ver_start.change(
            fn=_file.file_scan,
            inputs=file_scan_inputs,
            outputs=[
                version_progress,
                ver_finish
            ]
        )

        ver_finish.change(
            fn=_file.scan_finish,
            outputs=[
                ver_search,
                save_all_tags,
                load_installed,
                update_preview,
                organize_models,
                cancel_ver_search,
                load_to_browser
            ]
        )

        load_installed.click(
            fn=_file.installed_models_start,
            inputs=[installed_start],
            outputs=[
                installed_start,
                load_installed,
                cancel_installed,
                ver_search,
                save_all_tags,
                update_preview,
                organize_models,
                installed_progress
            ]
        )

        installed_start.change(
            fn=_file.file_scan,
            inputs=file_scan_inputs,
            outputs=[
                installed_progress,
                installed_finish
            ]
        )

        installed_finish.change(
            fn=_file.scan_finish,
            outputs=[
                ver_search,
                save_all_tags,
                load_installed,
                update_preview,
                organize_models,
                cancel_installed,
                load_to_browser_installed
            ]
        )

        save_all_tags.click(
            fn=_file.save_tag_start,
            inputs=[tag_start],
            outputs=[
                tag_start,
                save_all_tags,
                cancel_all_tags,
                load_installed,
                ver_search,
                update_preview,
                organize_models,
                tag_progress
            ]
        )

        tag_start.change(
            fn=_file.file_scan,
            inputs=file_scan_inputs,
            outputs=[
                tag_progress,
                tag_finish
            ]
        )

        tag_finish.change(
            fn=_file.save_tag_finish,
            outputs=[
                ver_search,
                save_all_tags,
                load_installed,
                update_preview,
                organize_models,
                cancel_all_tags
            ]
        )

        update_preview.click(
            fn=_file.save_preview_start,
            inputs=[preview_start],
            outputs=[
                preview_start,
                update_preview,
                cancel_update_preview,
                load_installed,
                ver_search,
                save_all_tags,
                organize_models,
                preview_progress
            ]
        )

        preview_start.change(
            fn=_file.file_scan,
            inputs=file_scan_inputs,
            outputs=[
                preview_progress,
                preview_finish
            ]
        )

        preview_finish.change(
            fn=_file.save_preview_finish,
            outputs=[
                ver_search,
                save_all_tags,
                load_installed,
                update_preview,
                organize_models,
                cancel_update_preview
            ]
        )

        organize_models.click(
            fn=_file.organize_start,
            inputs=[organize_start],
            outputs=[
                organize_start,
                organize_models,
                cancel_organize,
                load_installed,
                ver_search,
                save_all_tags,
                update_preview,
                organize_progress
            ]
        )

        organize_start.change(
            fn=_file.file_scan,
            inputs=file_scan_inputs,
            outputs=[
                organize_progress,
                organize_finish
            ]
        )

        organize_finish.change(
            fn=_file.save_preview_finish,
            outputs=[
                ver_search,
                save_all_tags,
                load_installed,
                update_preview,
                organize_models,
                cancel_update_preview
            ]
        )

        load_to_browser_installed.click(
            fn=_file.load_to_browser,
            inputs=load_to_browser_inputs,
            outputs=browser_installed_list
        )

        load_to_browser.click(
            fn=_file.load_to_browser,
            inputs=load_to_browser_inputs,
            outputs=browser_list
        )

        # Settings function
        create_subfolder.change(
            fn=_file.updateSubfolder,
            inputs=create_subfolder,
            outputs=[]
        )

    tab_name = 'CivitAI Browser+'
    return (civitai_interface, tab_name, 'civitai_interface'),

def subfolder_list(folder, desc=None):
    if folder == None:
        return
    model_folder = _api.contenttype_folder(folder, desc)
    sub_folders = _file.getSubfolders(model_folder)
    return sub_folders

def make_lambda(folder, desc):
    return lambda: {'choices': subfolder_list(folder, desc)}

## === ANXETY EDITs ===
def on_ui_settings():
    browser = ('civitai_browser', 'Browser')
    download = ('civitai_browser_download', 'Downloads')

    categories.register_category('civitai_browser_plus', 'CivitAI Browser+')
    cat_id = 'civitai_browser_plus'   # ANXETY: You have to name a variable like - pussy_id 🐱 :3

    if not (hasattr(shared.OptionInfo, 'info') and callable(getattr(shared.OptionInfo, 'info'))):
        def info(self, info):
            self.label += f" ({info})"
            return self
        shared.OptionInfo.info = info

    # Download Options
    shared.opts.add_option(
        'use_aria2',
        shared.OptionInfo(
            default=True,
            label='Download models using Aria2',
            section=download,
            category_id=cat_id
        ).info("Disable this option if you're experiencing any issues with downloads or if you want to use a proxy.")
    )

    shared.opts.add_option(
        'disable_dns',
        shared.OptionInfo(
            default=False,
            label='Disable Async DNS for Aria2',
            section=download,
            category_id=cat_id
        ).info('Useful for users who use PortMaster or other software that controls the DNS')
    )

    shared.opts.add_option(
        'show_log',
        shared.OptionInfo(
            default=False,
            label='Show Aria2 logs in console',
            section=download,
            category_id=cat_id
        ).info('Requires UI reload')
    )

    shared.opts.add_option(
        'split_aria2',
        shared.OptionInfo(
            default=64,
            label='Number of connections to use for downloading a model',
            component=gr.Slider,
            component_args=lambda: {'maximum': '64', 'minimum': '1', 'step': '1'},
            section=download,
            category_id=cat_id
        ).info('Only applies to Aria2')
    )

    shared.opts.add_option(
        'aria2_flags',
        shared.OptionInfo(
            default=r'',
            label='Custom Aria2 command line flags',
            section=download,
            category_id=cat_id
        ).info('Requires UI reload')
    )

    shared.opts.add_option(
        'unpack_zip',
        shared.OptionInfo(
            default=True,
            label='Automatically unpack .zip files after downloading',
            section=download,
            category_id=cat_id
        )
    )

    shared.opts.add_option(
        'save_api_info',
        shared.OptionInfo(
            default=False,
            label='Save API info of model when saving model info',
            section=download,
            category_id=cat_id
        ).info('creates an api_info.json file when saving any model info with all the API data of the model')
    )

    shared.opts.add_option(
        'auto_save_all_img',
        shared.OptionInfo(
            default=False,
            label='Automatically save all images',
            section=download,
            category_id=cat_id
        ).info('Automatically saves all the images of a model after downloading')
    )

    shared.opts.add_option(
        'save_img_count',
        shared.OptionInfo(
            default=16,
            label='Number of images to save',
            component=gr.Slider,
            component_args=lambda: {'maximum': '64', 'minimum': '4', 'step': '2'},
            section=download,
            category_id=cat_id
        ).info('Number of images to save when using the Save Images button or when auto_save_all_img is enabled')
    )

    shared.opts.add_option(
        'save_html_on_save',
        shared.OptionInfo(
            default=False,
            label='Save HTML file when saving model',
            section=download,
            category_id=cat_id
        ).info('If enabled, saves the HTML file locally when saving a model')
    )

    # Browser Options
    shared.opts.add_option(
        'custom_api_key',
        shared.OptionInfo(
            default=r'',
            label='Personal CivitAI API key',
            section=browser,
            category_id=cat_id
        ).info('You can create your own API key in your CivitAI account settings, this required for some downloads, Requires UI reload')
    )

    shared.opts.add_option(
        'hide_early_access',
        shared.OptionInfo(
            default=False,
            label='Hide early access models',
            section=browser,
            category_id=cat_id
        ).info('Early access models are only downloadable for supporter tier members')
    )

    shared.opts.add_option(
        'use_LORA',
        shared.OptionInfo(
            default=True,
            label='Combine LoCon, LORA & DoRA as one option',
            section=browser,
            category_id=cat_id
        )
    )

    shared.opts.add_option(
        'dot_subfolders',
        shared.OptionInfo(
            default=True,
            label='Hide sub-folders that start with a `.`',
            section=browser,
            category_id=cat_id
        )
    )

    shared.opts.add_option(
        'use_local_html',
        shared.OptionInfo(
            default=False,
            label='Use local HTML file for model info',
            section=browser,
            category_id=cat_id
        ).info('Uses the matching local HTML file when pressing CivitAI button on model cards in txt2img and img2img')
    )

    shared.opts.add_option(
        'local_path_in_html',
        shared.OptionInfo(
            default=False,
            label='Use local images in the HTML',
            section=browser,
            category_id=cat_id
        ).info('Only works if all images of the corresponding model are downloaded')
    )

    shared.opts.add_option(
        'page_header',
        shared.OptionInfo(
            default=False,
            label='Page navigation as header',
            section=browser,
            category_id=cat_id
        ).info('Keeps the page navigation always visible at the top, Requires UI reload')
    )

    shared.opts.add_option(
        'video_playback',
        shared.OptionInfo(
            default=True,
            label='Gif/video playback in the browser',
            section=browser,
            category_id=cat_id
        ).info("Disable this option if you're experiencing high CPU usage during video/gif playback")
    )

    shared.opts.add_option(
        'individual_meta_btn',
        shared.OptionInfo(
            default=True,
            label='Individual prompt buttons',
            section=browser,
            category_id=cat_id
        ).info('Turns individual prompts from an example image into a button to send it to txt2img')
    )

    shared.opts.add_option(
        'resize_preview_cards',
        shared.OptionInfo(
            default=True,
            label='Resize preview images/videos in model cards',
            section=browser,
            category_id=cat_id
        ).info('Resize preview images/videos in model cards to improve loading speeds')
    )

    shared.opts.add_option(
        'resize_preview_size',
        shared.OptionInfo(
            default=512,
            label='Preview resize size',
            component=gr.Slider,
            component_args=lambda: {'maximum': '1024', 'minimum': '128', 'step': '32'},
            section=browser,
            category_id=cat_id
        ).info('Size in pixels the width of preview images/videos. Images retain the aspect ratio.')
    )

    shared.opts.add_option(
        'resize_preview_on_save',
        shared.OptionInfo(
            default=True,
            label='Resize saved preview images',
            section=browser,
            category_id=cat_id
        ).info('Apply resizing to preview images when saving them locally?')
    )

    shared.opts.add_option(
        'model_desc_to_json',
        shared.OptionInfo(
            default=False,
            label='Save model description to json',
            section=browser,
            category_id=cat_id
        ).info('This saves the models description to the description field on model cards')
    )

    shared.opts.add_option(
        'civitai_send_to_browser',
        shared.OptionInfo(
            default=False,
            label='Send model from the cards CivitAI button to the browser, instead of showing a popup',
            section=browser,
            category_id=cat_id
        )
    )

    shared.opts.add_option(
        'image_location',
        shared.OptionInfo(
            default=r'',
            label='Custom save images location',
            section=browser,
            category_id=cat_id
        ).info('Overrides the download folder location when saving images.')
    )

    shared.opts.add_option(
        'sub_image_location',
        shared.OptionInfo(
            default=True,
            label='Use sub folders inside custom images location',
            section=browser,
            category_id=cat_id
        ).info('Will append any content type and sub folders to the custom path.')
    )

    shared.opts.add_option(
        'save_to_custom',
        shared.OptionInfo(
            default=False,
            label='Store the HTML and api_info in the custom images location',
            section=browser,
            category_id=cat_id
        )
    )

    shared.opts.add_option(
        'show_nsfw_badge',
        shared.OptionInfo(
            default=True,
            label='Show NSFW badge on model cards',
            section=browser,
            category_id=cat_id
        ).info('Display NSFW badge on model cards that are marked as NSFW content')
    )

    shared.opts.add_option(
        'custom_civitai_proxy',
        shared.OptionInfo(
            default=r'',
            label='Proxy address',
            component=gr.Textbox,
            component_args={'placeholder': 'socks4://0.0.0.0:00000 | socks5://0.0.0.0:00000'},
            section=browser,
            category_id=cat_id
        ).info('Only works with proxies that support HTTPS, turn Aria2 off for proxy downloads')
    )

    shared.opts.add_option(
        'cabundle_path_proxy',
        shared.OptionInfo(
            default=r'',
            label='Path to custom CA Bundle',
            component=gr.Textbox,
            component_args={'placeholder': '/path/to/custom/cabundle.pem'},
            section=browser,
            category_id=cat_id
        ).info('Specify custom CA bundle for SSL certificate checks if required')
    )

    shared.opts.add_option(
        'disable_sll_proxy',
        shared.OptionInfo(
            default=False,
            label='Disable SSL certificate checks',
            section=browser,
            category_id=cat_id
        ).info('Not recommended for security, may be required if you do not have the correct CA Bundle available')
    )

    shared.opts.add_option(
        'civitai_debug_prints',
        shared.OptionInfo(
            default=False,
            label='Enable debug prints',
            section=browser,
            category_id=cat_id
        ).info('Shows debug information in console for API calls and file operations. Requires UI reload')
    )

    # Default sub folders
    use_LORA = getattr(opts, 'use_LORA', False)
    folders = [
        'Checkpoint',
        'LORA, LoCon, DoRA' if use_LORA else 'LORA',
        'LoCon' if not use_LORA else None,
        'DoRA' if not use_LORA else None,
        'TextualInversion',
        'Poses',
        'Controlnet',
        'MotionModule',
        ('Upscaler', 'SWINIR'),
        ('Upscaler', 'REALESRGAN'),
        ('Upscaler', 'GFPGAN'),
        ('Upscaler', 'BSRGAN'),
        ('Upscaler', 'ESRGAN'),
        'VAE',
        'AestheticGradient',
        'Wildcards',
        'Workflows',
        'Other'
    ]

    for folder in folders:
        if folder is None:
            continue

        # Handle tuple folders (e.g., ('Upscaler', 'SWINIR'))
        if isinstance(folder, tuple):
            folder_name = f"{folder[0]} - {folder[1]}"
            setting_name = f"{folder[1]}_upscale"
            folder_key = folder[0]
            desc = folder[1]
        else:
            folder_name = folder
            setting_name = folder
            folder_key = folder
            desc = None

        # Special case for LORA, LoCon, DoRA
        if folder == 'LORA, LoCon, DoRA':
            folder_key = 'LORA'
            setting_name = 'LORA_LoCon'

        shared.opts.add_option(
            f"{setting_name}_default_subfolder",
            shared.OptionInfo(
                default='None',
                label=folder_name,
                component=gr.Dropdown,
                component_args=make_lambda(folder_key, desc),
                section=download,
                category_id=cat_id
            )
        )

script_callbacks.on_ui_tabs(on_ui_tabs)
script_callbacks.on_ui_settings(on_ui_settings)