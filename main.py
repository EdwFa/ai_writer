import streamlit as st
from groq import Groq
import json
import os
from io import BytesIO

# Ансамбль моделей
models = {
    "gemma-7b-it": {"name": "Gemma-7b-it", "tokens": 8192, "developer": "Google"},
    "llama3-70b-8192": {"name": "LLaMA3-70b-8192", "tokens": 8192, "developer": "Meta"},
    "llama3-8b-8192": {"name": "LLaMA3-8b-8192", "tokens": 8192, "developer": "Meta"},
    "mixtral-8x7b-32768": {"name": "Mixtral-8x7b-Instruct-v0.1", "tokens": 32768, "developer": "Mistral"},
}

# Ключи интер=фейсов
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", None)
if 'api_key' not in st.session_state:
    st.session_state.api_key = GROQ_API_KEY
if 'groq' not in st.session_state:
    if GROQ_API_KEY:
        st.session_state.groq = Groq()

# Формат страницы
st.set_page_config(page_icon="💬", layout="wide",
                   page_title="AI Писатель")
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""

# Параметры моделей
class AI_Model():
    def __init__(self, name="llama-3.1-8b-instant", version="8B", temperature=0.3, max_tokens=8192, top_P=1.0):
        self.name = name
        self.version = version
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_P = top_P
# иницифализация моделей для генерации структуры и контента
model_struct = AI_Model(name='llama-3.1-8b-instant', version='8B', temperature=0.2, max_tokens=8192, top_P=1.0)
model_content = AI_Model(name='llama-3.1-70b-versatile', version='70B', temperature=0.2, max_tokens=8192, top_P=1.0)

# Обрабатываем статистические параметры генерации 3.1 8b ламмой
class GenerationStatistics:
    def __init__(self, input_time=0,output_time=0,input_tokens=0,output_tokens=0,total_time=0,model_name="llama-3.1-8b-instant"):
        self.input_time = input_time
        self.output_time = output_time
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_time = total_time # Sum of queue, prompt (input), and completion (output) times
        self.model_name = model_name

    def get_input_speed(self):
        """ 
        Tokens per second calculation for input
        """
        if self.input_time != 0:
            return self.input_tokens / self.input_time
        else:
            return 0
    
    def get_output_speed(self):
        """ 
        Tokens per second calculation for output
        """
        if self.output_time != 0:
            return self.output_tokens / self.output_time
        else:
            return 0
    
    def add(self, other):
        """
        Add statistics from another GenerationStatistics object to this one.
        """
        if not isinstance(other, GenerationStatistics):
            raise TypeError("Can only add GenerationStatistics objects")
        
        self.input_time += other.input_time
        self.output_time += other.output_time
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.total_time += other.total_time

    def __str__(self):
        return (f"\n## {self.get_output_speed():.2f} T/s ⚡\nRound trip time: {self.total_time:.2f}s  Model: {self.model_name}\n\n"
                f"| Metric          | Input          | Output          | Total          |\n"
                f"|-----------------|----------------|-----------------|----------------|\n"
                f"| Speed (T/s)     | {self.get_input_speed():.2f}            | {self.get_output_speed():.2f}            | {(self.input_tokens + self.output_tokens) / self.total_time if self.total_time != 0 else 0:.2f}            |\n"
                f"| Tokens          | {self.input_tokens}            | {self.output_tokens}            | {self.input_tokens + self.output_tokens}            |\n"
                f"| Inference Time (s) | {self.input_time:.2f}            | {self.output_time:.2f}            | {self.total_time:.2f}            |")

# Книга
class Book:
    def __init__(self, structure):
        self.structure = structure
        self.contents = {title: "" for title in self.flatten_structure(structure)}
        self.placeholders = {title: st.empty() for title in self.flatten_structure(structure)}

        st.markdown("## Generating the following:")
        toc_columns = st.columns(4)
        self.display_toc(self.structure, toc_columns)
        st.markdown("---")

    def flatten_structure(self, structure):
        sections = []
        for title, content in structure.items():
            sections.append(title)
            if isinstance(content, dict):
                sections.extend(self.flatten_structure(content))
        return sections

    def update_content(self, title, new_content):
        try:
            self.contents[title] += new_content
            self.display_content(title)
        except TypeError as e:
            pass

    def display_content(self, title):
        if self.contents[title].strip():
            self.placeholders[title].markdown(f"## {title}\n{self.contents[title]}")

    def display_structure(self, structure=None, level=1):
        if structure is None:
            structure = self.structure
        
        for title, content in structure.items():
            if self.contents[title].strip():  # Only display title if there is content
                st.markdown(f"{'#' * level} {title}")
                self.placeholders[title].markdown(self.contents[title])
            if isinstance(content, dict):
                self.display_structure(content, level + 1)

    def display_toc(self, structure, columns, level=1, col_index=0):
        for title, content in structure.items():
            with columns[col_index % len(columns)]:
                st.markdown(f"{' ' * (level-1) * 2}- {title}")
            col_index += 1
            if isinstance(content, dict):
                col_index = self.display_toc(content, columns, level + 1, col_index)
        return col_index

    def get_markdown_content(self, structure=None, level=1):
        """
        Returns the markdown styled pure string with the contents.
        """
        if structure is None:
            structure = self.structure
        
        markdown_content = ""
        for title, content in structure.items():
            if self.contents[title].strip():  # Only include title if there is content
                markdown_content += f"{'#' * level} {title}\n{self.contents[title]}\n\n"
            if isinstance(content, dict):
                markdown_content += self.get_markdown_content(content, level + 1)
        return markdown_content

def create_markdown_file(content: str) -> BytesIO:
    """
    Create a Markdown file from the provided content.
    """
    markdown_file = BytesIO()
    markdown_file.write(content.encode('utf-8'))
    markdown_file.seek(0)
    return markdown_file

def generate_book_structure(prompt: str
                            # ai_model: AI_Model
                            ) -> dict:
    """
    Returns book structure content as well as total tokens and total time for generation.
    """
    ai_model = AI_Model(name="llama-3.1-8b-instant", version="8B", temperature=0.2, max_tokens=8192, top_P=1.0)
    prompt = task_struct + prompt
    st.info(prompt)
    completion = st.session_state.groq.chat.completions.create(
        model=ai_model.name,
        messages=[
            {
                "role": "system",
                "content": "Write in JSON format:\n\n{\"Title of section goes here\":\"Description of section goes here\",\n\"Title of section goes here\":{\"Title of section goes here\":\"Description of section goes here\",\"Title of section goes here\":\"Description of section goes here\",\"Title of section goes here\":\"Description of section goes here\"}}"
            },
            {
                "role": "user",
                "content": f"Write a comprehensive structure, omiting introduction and conclusion sections (forward, author's note, summary), for a long (>300 page) book on the following subject:\n\n<subject>{prompt}</subject>"
            }
        ],
        temperature=ai_model.temperature,
        max_tokens=ai_model.max_tokens,
        top_p=ai_model.top_P,
        stream=False,
        response_format={"type": "json_object"},
        stop = None,
    )

    usage = completion.usage
    statistics_to_return = GenerationStatistics(input_time=usage.prompt_time, output_time=usage.completion_time, input_tokens=usage.prompt_tokens, output_tokens=usage.completion_tokens, total_time=usage.total_time,model_name="llama3-8b-8192")

    return statistics_to_return, completion.choices[0].message.content

def generate_section(prompt: str):
    prompt = task_content + prompt
    stream = st.session_state.groq.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are an expert writer. Generate a long, comprehensive, structured chapter for the section provided."
            },
            {
                "role": "user",
                "content": f"Generate a long, comprehensive, structured chapter for the following section:\n\n<section_title>{prompt}</section_title>"
            }
        ],
        temperature=0.2,
        max_tokens=8192,
        top_p=1,
        stream=True,
        stop=None,
    )

    for chunk in stream:
        tokens = chunk.choices[0].delta.content
        if tokens:
            yield tokens
        if x_groq := chunk.x_groq:
            if not x_groq.usage:
                continue
            usage = x_groq.usage
            statistics_to_return = GenerationStatistics(input_time=usage.prompt_time, output_time=usage.completion_time, input_tokens=usage.prompt_tokens, output_tokens=usage.completion_tokens, total_time=usage.total_time,model_name="llama3-70b-8192")
            yield statistics_to_return

# Initialize
if 'button_disabled' not in st.session_state:
    st.session_state.button_disabled = False

if 'button_text' not in st.session_state:
    st.session_state.button_text = "Написать"

if 'statistics_text' not in st.session_state:
    st.session_state.statistics_text = ""

# Параметры модели структуры
st.sidebar.title('Структура')
model_struct_option = st.sidebar.selectbox(
    "Модель:",
    options=list(models.keys()),
    format_func=lambda x: models[x]["name"],
    index=1  # Default to llama3-70B
)
max_tokens_range_struct = models[model_struct_option]["tokens"]
max_tokens_struct = st.sidebar.slider(
    "Максимальное кол-во токенов:",
    min_value=512,  # Minimum value
    max_value=max_tokens_range_struct,
    # Default value or max allowed if less
    # value=min(32768, max_tokens_range_struct),
    value=8192,
    step=256,
    help=f"Настройте максимальное количество токенов для ответа модели. Для выбранной модели: {max_tokens_range_struct}"
)

task_struct = st.sidebar.text_area("Задача в структуру",
                        "When generating the structure "
                        "or content , "
                        "try to find and use the latest "
                        "knowledge and information on a given topic. ",
                     height = 64)

temp_struct = st.sidebar.number_input(
    "Установите температуру модели",
    min_value=0,
    max_value=200, value=30, step=1,
) / 100
top_P_struct = st.sidebar.slider(
    label = "Тop P :",
    min_value=0,  # Minimum value
    max_value=100,
    # Default value or max allowed if less
    value=100,
    step=1,
    help="Настройте параметр Top_P (по умолчанию=1)"
) / 100


# Параметры модели содержания
st.sidebar.title('Содержание')
model_content_option = st.sidebar.selectbox(
    "Модель",
    options=list(models.keys()),
    format_func=lambda x: models[x]["name"],
    index=2  # Default to llama3-8B
)
task_content = st.sidebar.text_area("По содержанию",
"When generating content, describe in detail the methods "
"used to diagnose or treat patients. Provide links only "
"to reliable sources of information that contain the necessary information. ",
                     height = 128)

max_tokens_range_content = models[model_content_option]["tokens"]
max_tokens_content = st.sidebar.slider(
    "Tокены контента",
    min_value=512,  # Minimum value
    max_value=max_tokens_range_content,
    # Default value or max allowed if less
    value=min(32768, max_tokens_range_content),
    step=256,
    help=f"Настройте максимальное количество токенов для ответа модели. Для выбранной модели: {max_tokens_range_content}"
)
temp_content = st.sidebar.number_input(
    "Tемпература контента",
    min_value=0,
    max_value=200, value=20, step=1,
) / 100
top_P_content = st.sidebar.slider(
    label = "Тop P в контенте",
    min_value=0,  # Minimum value
    max_value=100,
    # Default value or max allowed if less
    value=100,
    step=1,
    help="Настройте параметр Top_P (по умолчанию=1)"
) / 100

st.write("""
## Пишу книжки на заданную тему :)
""")

def disable():
    st.session_state.button_disabled = True

def enable():
    st.session_state.button_disabled = False

def empty_st():
    st.empty()

try:
    if st.button('Закончить генерацию'):
        if "book" in st.session_state:
            markdown_file = create_markdown_file(st.session_state.book.get_markdown_content())
            st.download_button(
                label='Выгрузить созданное',
                data=markdown_file,
                file_name='ai_book.md',
                mime='text/plain'
            )
        else:
            raise ValueError("Перед выгрузкой, пожалуйста создайте его :))")

    with st.form("groqform"):
        if not GROQ_API_KEY:
            # groq_input_key = st.text_input("Введите, выданный вам ключ ... : 👇", "",type="password")
            user_key = st.text_input("Введите, выданный вам ключ ... : 👇", "", type="password")
            if user_key == st.secrets["USER_KEY"]:
                groq_input_key = st.secrets["API_KEY"]

        topic_text = st.text_input("О чем вы хотите написать свою книгу? ", "")

        # Generate button
        submitted = st.form_submit_button(st.session_state.button_text,on_click=disable,disabled=st.session_state.button_disabled)
        
        # Statistics
        placeholder = st.empty()
        def display_statistics():
            with placeholder.container():
                if st.session_state.statistics_text:
                    if "Generating structure in background" not in st.session_state.statistics_text:
                        st.markdown(st.session_state.statistics_text+"\n\n---\n") # Format with line if showing statistics
                    else:
                        st.markdown(st.session_state.statistics_text)
                else:
                    placeholder.empty()

        if submitted:
            if len(topic_text)<20:
                raise ValueError("Тема книги не может быть менее 20 символов ")

            st.session_state.button_disabled = True
            # st.write("Generating structure in background....")
            st.session_state.statistics_text = "Generating structure in background...." # Show temporary message before structure is generated and statistics show
            display_statistics()

            if not GROQ_API_KEY:
                st.session_state.groq = Groq(api_key=groq_input_key)

            large_model_generation_statistics, book_structure = generate_book_structure(topic_text)

            st.session_state.statistics_text = str(large_model_generation_statistics)
            display_statistics()

            total_generation_statistics = GenerationStatistics(model_name="llama-3.1-8b-instant")

            try:
                book_structure_json = json.loads(book_structure)
                book = Book(book_structure_json)
                
                if 'book' not in st.session_state:
                    st.session_state.book = book

                # Print the book structure to the terminal to show structure
                print(json.dumps(book_structure_json, indent=2))

                st.session_state.book.display_structure()

                def stream_section_content(sections):
                    for title, content in sections.items():
                        if isinstance(content, str):
                            content_stream = generate_section(title+": "+content+task_content)
                            for chunk in content_stream:
                                # Check if GenerationStatistics data is returned instead of str tokens
                                chunk_data = chunk
                                if (type(chunk_data)==GenerationStatistics):
                                    total_generation_statistics.add(chunk_data)
                                    
                                    st.session_state.statistics_text = str(total_generation_statistics)
                                    display_statistics()

                                elif chunk!=None:
                                    st.session_state.book.update_content(title, chunk)
                        elif isinstance(content, dict):
                            stream_section_content(content)

                stream_section_content(book_structure_json)
            
            except json.JSONDecodeError:
                st.error("Failed to decode the book structure. Please try again.")

            enable()

except Exception as e:
    st.session_state.button_disabled = False
    st.error(e)

    if st.button("Очистить"):
        st.rerun()