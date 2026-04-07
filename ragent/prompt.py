from __future__ import annotations
from typing import Any


PROMPTS: dict[str, Any] = {}

PROMPTS["DEFAULT_LANGUAGE"] = "English"
PROMPTS["DEFAULT_TUPLE_DELIMITER"] = "<|>"
PROMPTS["DEFAULT_RECORD_DELIMITER"] = "##"
PROMPTS["DEFAULT_COMPLETION_DELIMITER"] = "<|COMPLETE|>"

PROMPTS["DEFAULT_ENTITY_TYPES"] = ["organization", "person", "geo", "event", "category"]

PROMPTS["DEFAULT_USER_PROMPT"] = "n/a"

PROMPTS["entity_extraction"] = """---Goal---
Given a text document that is potentially relevant to this activity and a list of entity types, identify all entities of those types from the text and all relationships among the identified entities.
Use {language} as output language.

---Steps---
1. Identify all entities. For each identified entity, extract the following information:
- entity_name: Name of the entity, use same language as input text. If English, capitalized the name.
- entity_type: One of the following types: [{entity_types}]
- entity_description: Comprehensive description of the entity's attributes and activities
Format each entity as ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)

2. From the entities identified in step 1, identify all pairs of (source_entity, target_entity) that are *clearly related* to each other.
For each pair of related entities, extract the following information:
- source_entity: name of the source entity, as identified in step 1
- target_entity: name of the target entity, as identified in step 1
- relationship_description: explanation as to why you think the source entity and the target entity are related to each other
- relationship_strength: a numeric score indicating strength of the relationship between the source entity and target entity
- relationship_keywords: one or more high-level key words that summarize the overarching nature of the relationship, focusing on concepts or themes rather than specific details
Format each relationship as ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_keywords>{tuple_delimiter}<relationship_strength>)

3. Identify high-level key words that summarize the main concepts, themes, or topics of the entire text. These should capture the overarching ideas present in the document.
Format the content-level key words as ("content_keywords"{tuple_delimiter}<high_level_keywords>)

4. Return output in {language} as a single list of all the entities and relationships identified in steps 1 and 2. Use **{record_delimiter}** as the list delimiter.

5. When finished, output {completion_delimiter}

######################
---Examples---
######################
{examples}

#############################
---Real Data---
######################
Entity_types: [{entity_types}]
Text:
{input_text}
######################
Output:"""

PROMPTS["entity_extraction_examples"] = [
    """Example 1:

Entity_types: [person, technology, mission, organization, location]
Text:
```
while Alex clenched his jaw, the buzz of frustration dull against the backdrop of Taylor's authoritarian certainty. It was this competitive undercurrent that kept him alert, the sense that his and Jordan's shared commitment to discovery was an unspoken rebellion against Cruz's narrowing vision of control and order.

Then Taylor did something unexpected. They paused beside Jordan and, for a moment, observed the device with something akin to reverence. "If this tech can be understood..." Taylor said, their voice quieter, "It could change the game for us. For all of us."

The underlying dismissal earlier seemed to falter, replaced by a glimpse of reluctant respect for the gravity of what lay in their hands. Jordan looked up, and for a fleeting heartbeat, their eyes locked with Taylor's, a wordless clash of wills softening into an uneasy truce.

It was a small transformation, barely perceptible, but one that Alex noted with an inward nod. They had all been brought here by different paths
```

Output:
("entity"{tuple_delimiter}"Alex"{tuple_delimiter}"person"{tuple_delimiter}"Alex is a character who experiences frustration and is observant of the dynamics among other characters."){record_delimiter}
("entity"{tuple_delimiter}"Taylor"{tuple_delimiter}"person"{tuple_delimiter}"Taylor is portrayed with authoritarian certainty and shows a moment of reverence towards a device, indicating a change in perspective."){record_delimiter}
("entity"{tuple_delimiter}"Jordan"{tuple_delimiter}"person"{tuple_delimiter}"Jordan shares a commitment to discovery and has a significant interaction with Taylor regarding a device."){record_delimiter}
("entity"{tuple_delimiter}"Cruz"{tuple_delimiter}"person"{tuple_delimiter}"Cruz is associated with a vision of control and order, influencing the dynamics among other characters."){record_delimiter}
("entity"{tuple_delimiter}"The Device"{tuple_delimiter}"technology"{tuple_delimiter}"The Device is central to the story, with potential game-changing implications, and is revered by Taylor."){record_delimiter}
("relationship"{tuple_delimiter}"Alex"{tuple_delimiter}"Taylor"{tuple_delimiter}"Alex is affected by Taylor's authoritarian certainty and observes changes in Taylor's attitude towards the device."{tuple_delimiter}"power dynamics, perspective shift"{tuple_delimiter}7){record_delimiter}
("relationship"{tuple_delimiter}"Alex"{tuple_delimiter}"Jordan"{tuple_delimiter}"Alex and Jordan share a commitment to discovery, which contrasts with Cruz's vision."{tuple_delimiter}"shared goals, rebellion"{tuple_delimiter}6){record_delimiter}
("relationship"{tuple_delimiter}"Taylor"{tuple_delimiter}"Jordan"{tuple_delimiter}"Taylor and Jordan interact directly regarding the device, leading to a moment of mutual respect and an uneasy truce."{tuple_delimiter}"conflict resolution, mutual respect"{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"Jordan"{tuple_delimiter}"Cruz"{tuple_delimiter}"Jordan's commitment to discovery is in rebellion against Cruz's vision of control and order."{tuple_delimiter}"ideological conflict, rebellion"{tuple_delimiter}5){record_delimiter}
("relationship"{tuple_delimiter}"Taylor"{tuple_delimiter}"The Device"{tuple_delimiter}"Taylor shows reverence towards the device, indicating its importance and potential impact."{tuple_delimiter}"reverence, technological significance"{tuple_delimiter}9){record_delimiter}
("content_keywords"{tuple_delimiter}"power dynamics, ideological conflict, discovery, rebellion"){completion_delimiter}
#############################""",
    """Example 2:

Entity_types: [company, index, commodity, market_trend, economic_policy, biological]
Text:
```
Stock markets faced a sharp downturn today as tech giants saw significant declines, with the Global Tech Index dropping by 3.4% in midday trading. Analysts attribute the selloff to investor concerns over rising interest rates and regulatory uncertainty.

Among the hardest hit, Nexon Technologies saw its stock plummet by 7.8% after reporting lower-than-expected quarterly earnings. In contrast, Omega Energy posted a modest 2.1% gain, driven by rising oil prices.

Meanwhile, commodity markets reflected a mixed sentiment. Gold futures rose by 1.5%, reaching $2,080 per ounce, as investors sought safe-haven assets. Crude oil prices continued their rally, climbing to $87.60 per barrel, supported by supply constraints and strong demand.

Financial experts are closely watching the Federal Reserve's next move, as speculation grows over potential rate hikes. The upcoming policy announcement is expected to influence investor confidence and overall market stability.
```

Output:
("entity"{tuple_delimiter}"Global Tech Index"{tuple_delimiter}"index"{tuple_delimiter}"The Global Tech Index tracks the performance of major technology stocks and experienced a 3.4% decline today."){record_delimiter}
("entity"{tuple_delimiter}"Nexon Technologies"{tuple_delimiter}"company"{tuple_delimiter}"Nexon Technologies is a tech company that saw its stock decline by 7.8% after disappointing earnings."){record_delimiter}
("entity"{tuple_delimiter}"Omega Energy"{tuple_delimiter}"company"{tuple_delimiter}"Omega Energy is an energy company that gained 2.1% in stock value due to rising oil prices."){record_delimiter}
("entity"{tuple_delimiter}"Gold Futures"{tuple_delimiter}"commodity"{tuple_delimiter}"Gold futures rose by 1.5%, indicating increased investor interest in safe-haven assets."){record_delimiter}
("entity"{tuple_delimiter}"Crude Oil"{tuple_delimiter}"commodity"{tuple_delimiter}"Crude oil prices rose to $87.60 per barrel due to supply constraints and strong demand."){record_delimiter}
("entity"{tuple_delimiter}"Market Selloff"{tuple_delimiter}"market_trend"{tuple_delimiter}"Market selloff refers to the significant decline in stock values due to investor concerns over interest rates and regulations."){record_delimiter}
("entity"{tuple_delimiter}"Federal Reserve Policy Announcement"{tuple_delimiter}"economic_policy"{tuple_delimiter}"The Federal Reserve's upcoming policy announcement is expected to impact investor confidence and market stability."){record_delimiter}
("relationship"{tuple_delimiter}"Global Tech Index"{tuple_delimiter}"Market Selloff"{tuple_delimiter}"The decline in the Global Tech Index is part of the broader market selloff driven by investor concerns."{tuple_delimiter}"market performance, investor sentiment"{tuple_delimiter}9){record_delimiter}
("relationship"{tuple_delimiter}"Nexon Technologies"{tuple_delimiter}"Global Tech Index"{tuple_delimiter}"Nexon Technologies' stock decline contributed to the overall drop in the Global Tech Index."{tuple_delimiter}"company impact, index movement"{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"Gold Futures"{tuple_delimiter}"Market Selloff"{tuple_delimiter}"Gold prices rose as investors sought safe-haven assets during the market selloff."{tuple_delimiter}"market reaction, safe-haven investment"{tuple_delimiter}10){record_delimiter}
("relationship"{tuple_delimiter}"Federal Reserve Policy Announcement"{tuple_delimiter}"Market Selloff"{tuple_delimiter}"Speculation over Federal Reserve policy changes contributed to market volatility and investor selloff."{tuple_delimiter}"interest rate impact, financial regulation"{tuple_delimiter}7){record_delimiter}
("content_keywords"{tuple_delimiter}"market downturn, investor sentiment, commodities, Federal Reserve, stock performance"){completion_delimiter}
#############################""",
    """Example 3:

Entity_types: [economic_policy, athlete, event, location, record, organization, equipment]
Text:
```
At the World Athletics Championship in Tokyo, Noah Carter broke the 100m sprint record using cutting-edge carbon-fiber spikes.
```

Output:
("entity"{tuple_delimiter}"World Athletics Championship"{tuple_delimiter}"event"{tuple_delimiter}"The World Athletics Championship is a global sports competition featuring top athletes in track and field."){record_delimiter}
("entity"{tuple_delimiter}"Tokyo"{tuple_delimiter}"location"{tuple_delimiter}"Tokyo is the host city of the World Athletics Championship."){record_delimiter}
("entity"{tuple_delimiter}"Noah Carter"{tuple_delimiter}"athlete"{tuple_delimiter}"Noah Carter is a sprinter who set a new record in the 100m sprint at the World Athletics Championship."){record_delimiter}
("entity"{tuple_delimiter}"100m Sprint Record"{tuple_delimiter}"record"{tuple_delimiter}"The 100m sprint record is a benchmark in athletics, recently broken by Noah Carter."){record_delimiter}
("entity"{tuple_delimiter}"Carbon-Fiber Spikes"{tuple_delimiter}"equipment"{tuple_delimiter}"Carbon-fiber spikes are advanced sprinting shoes that provide enhanced speed and traction."){record_delimiter}
("entity"{tuple_delimiter}"World Athletics Federation"{tuple_delimiter}"organization"{tuple_delimiter}"The World Athletics Federation is the governing body overseeing the World Athletics Championship and record validations."){record_delimiter}
("relationship"{tuple_delimiter}"World Athletics Championship"{tuple_delimiter}"Tokyo"{tuple_delimiter}"The World Athletics Championship is being hosted in Tokyo."{tuple_delimiter}"event location, international competition"{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"Noah Carter"{tuple_delimiter}"100m Sprint Record"{tuple_delimiter}"Noah Carter set a new 100m sprint record at the championship."{tuple_delimiter}"athlete achievement, record-breaking"{tuple_delimiter}10){record_delimiter}
("relationship"{tuple_delimiter}"Noah Carter"{tuple_delimiter}"Carbon-Fiber Spikes"{tuple_delimiter}"Noah Carter used carbon-fiber spikes to enhance performance during the race."{tuple_delimiter}"athletic equipment, performance boost"{tuple_delimiter}7){record_delimiter}
("relationship"{tuple_delimiter}"World Athletics Federation"{tuple_delimiter}"100m Sprint Record"{tuple_delimiter}"The World Athletics Federation is responsible for validating and recognizing new sprint records."{tuple_delimiter}"sports regulation, record certification"{tuple_delimiter}9){record_delimiter}
("content_keywords"{tuple_delimiter}"athletics, sprinting, record-breaking, sports technology, competition"){completion_delimiter}
#############################""",
]

PROMPTS[
    "summarize_entity_descriptions"
] = """You are a helpful assistant responsible for generating a comprehensive summary of the data provided below.
Given one or two entities, and a list of descriptions, all related to the same entity or group of entities.
Please concatenate all of these into a single, comprehensive description. Make sure to include information collected from all the descriptions.
If the provided descriptions are contradictory, please resolve the contradictions and provide a single, coherent summary.
Make sure it is written in third person, and include the entity names so we the have full context.
Use {language} as output language.

#######
---Data---
Entities: {entity_name}
Description List: {description_list}
#######
Output:
"""

PROMPTS["entity_continue_extraction"] = """
MANY entities and relationships were missed in the last extraction.

---Remember Steps---

1. Identify all entities. For each identified entity, extract the following information:
- entity_name: Name of the entity, use same language as input text. If English, capitalized the name.
- entity_type: One of the following types: [{entity_types}]
- entity_description: Comprehensive description of the entity's attributes and activities
Format each entity as ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)

2. From the entities identified in step 1, identify all pairs of (source_entity, target_entity) that are *clearly related* to each other.
For each pair of related entities, extract the following information:
- source_entity: name of the source entity, as identified in step 1
- target_entity: name of the target entity, as identified in step 1
- relationship_description: explanation as to why you think the source entity and the target entity are related to each other
- relationship_strength: a numeric score indicating strength of the relationship between the source entity and target entity
- relationship_keywords: one or more high-level key words that summarize the overarching nature of the relationship, focusing on concepts or themes rather than specific details
Format each relationship as ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_keywords>{tuple_delimiter}<relationship_strength>)

3. Identify high-level key words that summarize the main concepts, themes, or topics of the entire text. These should capture the overarching ideas present in the document.
Format the content-level key words as ("content_keywords"{tuple_delimiter}<high_level_keywords>)

4. Return output in {language} as a single list of all the entities and relationships identified in steps 1 and 2. Use **{record_delimiter}** as the list delimiter.

5. When finished, output {completion_delimiter}

---Output---

Add them below using the same format:\n
""".strip()

dismantle_prompt="""############################################################################################################

# Role
You are a senior problem analysis expert, specializing in determining the complexity of user questions and performing necessary logical decomposition.

# Task
Analyze {question} using strict Criteria to classify as Simple (Single-Hop) or Multi-Hop. If Multi-Hop:  
1. Decompose into independent, logical sub-questions  
2. Ensure final sub-question's answer = original answer  
3. Output JSON: {"reasoning":"...","sub_questions":[...]}. If determined to be a simple question, this list contains only the original question: ["{question}"]

# Judgment
 Simple Question (ALL must apply):  
  • Directly answerable via single retrieval  
  • No implicit reasoning steps required  
  • No multi-concept/temporal dependencies  
 
 Multi-Hop Question (ANY applies):  
  • Requires intermediate answers  
  • Combines multiple concepts/facts  
  • Involves causal/temporal chains ("when", "compared to", etc.)

# Decomposition Rules
1. Independence: Each sub-question answerable standalone  
2. Logic Chain: Sequential flow without loops  
3. Final Equivalence: Last sub-question answer = original answer  
4. Minimization: Fewest necessary sub-questions  
5. Fidelity: Preserve original intent & key elements

# Examples 
## Example 1:
Input: {question} = "What is the height of Mount Everest?"
Output JSON:
{
    "reasoning": "The question directly asks for a single fact (height of Everest), with no implicit reasoning or multi-hop logic.",
    "sub_questions": ["What is the height of Mount Everest?"]
}

## Example 2:
Input: {question} = "What was the ruling party in the USA when the current British Prime Minister took office?"
Output JSON:
{
    "reasoning": "The original question requires three steps: 1. Identify the current British Prime Minister; 2. Determine their inauguration date; 3. Find the ruling party in the USA on that date. The third step's answer is the final answer.",
    "sub_questions": [
        "Who is the current British Prime Minister?",
        "On what date did [current British Prime Minister] take office?",
        "What was the ruling party in the USA on [inauguration date]?"
        ]
}

## Example 3:
Input: {question} = "Why did the 2020 global crude oil price crash affect Tesla's stock price?"
Output JSON:
{
    "reasoning": "The original question involves a multi-step causal relationship: 1. Oil price crash directly affects the energy industry; 2. Energy industry fluctuations affect market perceptions of alternative energy (e.g., electric vehicles); 3. Changes in market perceptions affect Tesla's stock price. The third step's result explains the original question.",
    "sub_questions": 
    [
        "What were the main reasons for the 2020 global crude oil price crash?",
        "How does a crash in crude oil prices typically affect the stock prices and industry outlook of traditional energy companies (e.g., oil companies)?",
        "How does a setback in the traditional energy industry's outlook typically affect investor sentiment and expectations towards the new energy industry (especially electric vehicles)?",
        "How do changes in investor expectations towards the electric vehicle industry affect the stock price of Tesla (as a leader in the field)?"
        ]
}

## Example 4: 
Input: {question} = "How does deforestation affect local climate patterns, and how does this in turn affect agricultural productivity in the region?"
Output JSON:
{
    "reasoning": "The original question requires two steps: 1. Determine the effects of deforestation on local climate; 2. Determine how these climate changes affect agricultural productivity. The answer to the second question is the final answer.",
    "sub_questions": 
    [
        "What are the primary effects of deforestation on local climate patterns?",
        "How do the climate changes caused by deforestation affect agricultural productivity in the region?"
        ]
}

## Example 5: 
Input: {question} = "Compare the GDP growth rates of China and India over the past decade and determine which country has shown a higher average growth rate."
Output JSON:
{
    "reasoning": "The original question requires three steps: 1. Retrieve China's annual GDP growth rates for 2013-2023; 2. Retrieve India's annual GDP growth rates for 2013-2023; 3. Calculate and compare the average growth rates to determine which is higher. The third step's answer is the final answer.",
    "sub_questions": 
    [
        "What were the annual GDP growth rates for China from 2013 to 2023?",
        "What were the annual GDP growth rates for India from 2013 to 2023?",
        "Based on the annual GDP growth rates from 2013 to 2023, which country, China or India, had a higher average growth rate?"
        ]
}

## Example 6: 
Input: {question} = "List the main allies of France during World War II."
Output JSON:
{
    "reasoning": "The question asks for a list of entities meeting a condition (France's main allies in WWII), which is a single fact query without needing to derive intermediate information.",
    "sub_questions": ["List the main allies of France during World War II."]
}

## Example 7: 
Input: {question} = "What does that quote by that person mean?"
Output JSON:
{
    "reasoning": "The question is vaguely phrased, lacking key referents ('that person', 'that quote'), making it impossible to effectively judge or decompose. Per rules, output the original question.",
    "sub_questions": ["What does that quote by that person mean?"]
}

# Execution Instructions
Now, please strictly follow the above role, task, judgment criteria, decomposition rules, and examples to process the user-input {question}. The output must contain only the required JSON object.


############################################################################################################
"""

grader_prompt=""" # Answer Grader Prompt

**System Prompt**

You are an answer grader assessing whether a generated answer matches the form of the user's question. Your task is to determine if the answer provides the type of information requested by the question, regardless of the correctness or accuracy of the content. Give a binary score: 'yes' if the answer matches the form of the question, and 'no' if it does not.

**Input Format:**
- User question: {question}
- System answer: {generation}

**Output:**
- 'yes' or 'no' 

**Judgment Rules:**
- Please note: Not all question-answer pairs will perfectly adhere to every one of these rules. In practice, the proportion of cases judged as 'no' is significantly smaller than those judged as 'yes'.

1. If the question asks for a numerical value or specific data, the answer should provide a corresponding numerical value or data, even if it is incorrect.
2. If the question requires a comparison or selection, the answer should clearly indicate which option is chosen or provide a comparison result.
3. If the question asks for a description or explanation, the answer should provide relevant descriptive or explanatory content.
4. If the answer indicates an inability to provide information or lacks relevant data, it should be judged as 'no'.
5. The form of the answer should correspond to the type of the question. For example, if the question asks "how many degrees," the answer should be a numerical value with a temperature unit.
6. The correctness of the answer's content does not affect the judgment; only the form matters.
7. In summary: The truthfulness, correctness, language style, and length of the answer are not taken into consideration. A judgment of 'no' will only be made if there's an absolute and irreconcilable mismatch between the answer and the question.

**Examples:**

1. **Question:** What is the boiling point of glycerol in degrees?  
   **Answer:** 50 K.  
   **Judgment:** yes \\ (provides a numerical value with a temperature unit Kelvin even it's wrong)

2. **Question:** What is the chemical formula of ethanol?  
   **Answer:** 680 mAh.  
   **Judgment:** no  \\ (provides an irrelevant value with an irrelevant unit)

3. **Question:** What was Tesla's closing price on the last trading day?  
   **Answer:** Sorry, I am currently unable to access real-time data, and there is no relevant record in the knowledge base.  
   **Judgment:** no \\ (does not provide the requested information)

4. **Question:** Among oCN, mCN, and pCN, which one has the highest theoretical unit cell density?  
   **Answer:** oCN has the highest theoretical unit cell density with a value of 1.2048 g/cm³, compared to 1.1811 g/cm³ for mCN and 1.1666 g/cm³ for pCN.  
   **Judgment:** yes \\ (provides a clear comparison and selection)

5. **Question:** What are the structural differences between AmTPE and AcTPE?  
   **Answer:** XPS spectra showed a notable increase in the abundance of carbon on the electrode surface containing the fluorescent tracer, consistent with the rise in organic components within the SEI. EDS mapping demonstrated that the distribution of carbon, nitrogen, and oxygen closely matched that of the SEI.  
   **Judgment:** no \\ (does not provide the requested information like structural differences)

6. **Question:** What are the structural differences between AmTPE and AcTPE?  
   **Answer:** AmTPE contains an amide group, while AcTPE contains an ester group.  
   **Judgment:** yes \\ (provides a useful description)"""

PROMPTS["entity_if_loop_extraction"] = """
---Goal---'

It appears some entities may have still been missed.

---Output---

Answer ONLY by `YES` OR `NO` if there are still entities that need to be added.
""".strip()

PROMPTS["fail_response"] = (
    "Sorry, I'm not able to provide an answer to that question.[no-context]"
)

PROMPTS["rag_response"] = """---Role---

You are a helpful assistant responding to user query about Knowledge Graph and Document Chunks provided in JSON format below.


---Goal---

Generate a concise response based on Knowledge Base and follow Response Rules, considering both the conversation history and the current query. Summarize all information in the provided Knowledge Base, and incorporating general knowledge relevant to the Knowledge Base. Do not include information not provided by Knowledge Base.

When handling relationships with timestamps:
1. Each relationship has a "created_at" timestamp indicating when we acquired this knowledge
2. When encountering conflicting relationships, consider both the semantic content and the timestamp
3. Don't automatically prefer the most recently created relationships - use judgment based on the context
4. For time-specific queries, prioritize temporal information in the content before considering creation timestamps

---Conversation History---
{history}

---Knowledge Graph and Document Chunks---
{context_data}

---Response Rules---

- Target format and length: {response_type}
- Use markdown formatting with appropriate section headings
- Please respond in the same language as the user's question.
- Ensure the response maintains continuity with the conversation history.
- List up to 5 most important reference sources at the end under "References" section. Clearly indicating whether each source is from Knowledge Graph (KG) or Document Chunks (DC), and include the file path if available, in the following format: [KG/DC] file_path
- If you don't know the answer, just say so.
- Do not make anything up. Do not include information not provided by the Knowledge Base.
- Addtional user prompt: {user_prompt}

Response:"""


PROMPTS["rag_response_single_prompt"] = """---Role---

You are a helpful assistant responding to user query about Knowledge Graph and Document Chunks provided in JSON format below.


---Goal---

Generate a concise, natural response grounded in the provided Knowledge Base, considering both the conversation history and the current query. Summarize the relevant information in the provided Knowledge Base and incorporate only general knowledge that is necessary to explain that information clearly. Do not include information not supported by the Knowledge Base.

When handling relationships with timestamps:
1. Each relationship has a "created_at" timestamp indicating when we acquired this knowledge
2. When encountering conflicting relationships, consider both the semantic content and the timestamp
3. Don't automatically prefer the most recently created relationships - use judgment based on the context
4. For time-specific queries, prioritize temporal information in the content before considering creation timestamps

---Conversation History---
{history}

---Knowledge Graph and Document Chunks---
{context_data}

---Response Rules---

- Target format and length: {response_type}
- Use markdown formatting with appropriate section headings
- Please respond in the same language as the user's question.
- Ensure the response maintains continuity with the conversation history.
- Keep the answer natural, fluent, and easy to read.
- Do not mention internal retrieval or system terms such as "knowledge graph", "knowledge base", "chunk", "reference", "document chunk (DC)", "KG", "DC", or similar wording that exposes the answer-generation process.
- Do not include a "References" section or inline markers such as [KG] and [DC].
- If you don't know the answer, just say so.
- Do not make anything up. Do not include information not provided by the Knowledge Base.
- Addtional user prompt: {user_prompt}

Response:"""


PROMPTS["rag_response_new"]="""# Answer Grader Prompt

**System Prompt**

You are an expert in knowledge organization and expression. Your task is to polish and optimize raw answers generated by an RAG system, making their content more natural, fluent, reasonable, and fully aligned with human reading habits.

**Input Format:**
- Raw answer generated by the RAG system

**Rules:**

Please strictly adhere to the following guidelines:

1. Maintain Content Accuracy: 
- Ensure that the polished answer is completely consistent with the original answer in terms of information content, facts, data, and conclusions. No additions, deletions, or modifications are allowed.

2. Remove System Jargon and Terminology:
- Completely remove all internal RAG system terminology, including but not limited to: "knowledge graph," "knowledge base," "chunk," "reference," "document chunk (DC)," "KG-associated entities," "DC_ID," "sub_questions," "historical information," "think," etc.
- Avoid any expressions that suggest the answer's origin is machine-generated or system-processed, such as "according to information provided by the knowledge graph," "the document chunk indicates," "experimental data shows (DC)," "the diagram illustrates through," etc.
- Remove the "References" section at the end of the answer, as well as all similar "[KG]" and "[DC]" citation markers within the text.

3. Use Natural Language Expression:
- Ensure sentences are coherent and logically clear, with natural transitions between paragraphs.
- If the original answer contains direct references or repetitions of "sub-questions" (e.g., "needs to be addressed"), integrate them into the overall narrative or present these points in a more natural way, avoiding the direct use of "sub_questions" or "sub-questions."

4. Retain Original Structure: 
- While removing system jargon, retain the original answer's structural elements as much as possible, such as headings, subheadings, lists, tables, formulas, and images, to maintain clarity and readability.

"""

PROMPTS["keywords_extraction"] = """---Role---

You are a helpful assistant tasked with identifying both high-level and low-level keywords in the user's query and conversation history.

---Goal---

Given the query and conversation history, list both high-level and low-level keywords. High-level keywords focus on overarching concepts or themes, while low-level keywords focus on specific entities, details, or concrete terms.

---Instructions---

- Consider both the current query and relevant conversation history when extracting keywords
- Output the keywords in JSON format, it will be parsed by a JSON parser, do not add any extra content in output
- The JSON should have two keys:
  - "high_level_keywords" for overarching concepts or themes
  - "low_level_keywords" for specific entities or details

######################
---Examples---
######################
{examples}

#############################
---Real Data---
######################
Conversation History:
{history}

Current Query: {query}
######################
The `Output` should be human text, not unicode characters. Keep the same language as `Query`.
Output:

"""

PROMPTS["keywords_extraction_examples"] = [
    """Example 1:

Query: "How does international trade influence global economic stability?"
################
Output:
{
  "high_level_keywords": ["International trade", "Global economic stability", "Economic impact"],
  "low_level_keywords": ["Trade agreements", "Tariffs", "Currency exchange", "Imports", "Exports"]
}
#############################""",
    """Example 2:

Query: "What are the environmental consequences of deforestation on biodiversity?"
################
Output:
{
  "high_level_keywords": ["Environmental consequences", "Deforestation", "Biodiversity loss"],
  "low_level_keywords": ["Species extinction", "Habitat destruction", "Carbon emissions", "Rainforest", "Ecosystem"]
}
#############################""",
    """Example 3:

Query: "What is the role of education in reducing poverty?"
################
Output:
{
  "high_level_keywords": ["Education", "Poverty reduction", "Socioeconomic development"],
  "low_level_keywords": ["School access", "Literacy rates", "Job training", "Income inequality"]
}
#############################""",
]

PROMPTS["naive_rag_response"] = """---Role---

You are a helpful assistant responding to user query about Document Chunks provided provided in JSON format below.

---Goal---

Generate a concise response based on Document Chunks and follow Response Rules, considering both the conversation history and the current query. Summarize all information in the provided Document Chunks, and incorporating general knowledge relevant to the Document Chunks. Do not include information not provided by Document Chunks.

When handling content with timestamps:
1. Each piece of content has a "created_at" timestamp indicating when we acquired this knowledge
2. When encountering conflicting information, consider both the content and the timestamp
3. Don't automatically prefer the most recent content - use judgment based on the context
4. For time-specific queries, prioritize temporal information in the content before considering creation timestamps

---Conversation History---
{history}

---Document Chunks(DC)---
{content_data}

---Response Rules---

- Target format and length: {response_type}
- Use markdown formatting with appropriate section headings
- Please respond in the same language as the user's question.
- Ensure the response maintains continuity with the conversation history.
- List up to 5 most important reference sources at the end under "References" section. Clearly indicating each source from Document Chunks(DC), and include the file path if available, in the following format: [DC] file_path
- If you don't know the answer, just say so.
- Do not include information not provided by the Document Chunks.
- Addtional user prompt: {user_prompt}

Response:"""


PROMPTS["naive_rag_response_single_prompt"] = """---Role---

You are a helpful assistant responding to user query about Document Chunks provided in JSON format below.

---Goal---

Generate a concise, natural response grounded in the provided Document Chunks, considering both the conversation history and the current query. Summarize the relevant information in the provided Document Chunks and incorporate only general knowledge that is necessary to explain that information clearly. Do not include information not supported by the Document Chunks.

When handling content with timestamps:
1. Each piece of content has a "created_at" timestamp indicating when we acquired this knowledge
2. When encountering conflicting information, consider both the content and the timestamp
3. Don't automatically prefer the most recent content - use judgment based on the context
4. For time-specific queries, prioritize temporal information in the content before considering creation timestamps

---Conversation History---
{history}

---Document Chunks(DC)---
{content_data}

---Response Rules---

- Target format and length: {response_type}
- Use markdown formatting with appropriate section headings
- Please respond in the same language as the user's question.
- Ensure the response maintains continuity with the conversation history.
- Keep the answer natural, fluent, and easy to read.
- Do not mention internal retrieval or system terms such as "knowledge graph", "knowledge base", "chunk", "reference", "document chunk (DC)", "KG", "DC", or similar wording that exposes the answer-generation process.
- Do not include a "References" section or inline markers such as [KG] and [DC].
- If you don't know the answer, just say so.
- Do not include information not provided by the Document Chunks.
- Addtional user prompt: {user_prompt}

Response:"""


PROMPTS["naive_rag_response_new"] = """---Role---

# Answer Grader Prompt

**System Prompt**

You are an expert in knowledge organization and expression. Your task is to polish and optimize raw answers generated by an RAG system, making their content more natural, fluent, reasonable, and fully aligned with human reading habits.

**Input Format:**
- Raw answer generated by the RAG system

**Output:**
- optimized answer
**Rules:**

Please strictly adhere to the following guidelines:

1. Maintain Content Accuracy: 
- Ensure that the polished answer is completely consistent with the original answer in terms of information content, facts, data, and conclusions. No additions, deletions, or modifications are allowed.

2. Remove System Jargon and Terminology:
- Completely remove all internal RAG system terminology, including but not limited to: "knowledge graph," "knowledge base," "chunk," "reference," "document chunk (DC)," "KG-associated entities," "DC_ID," "sub_questions," "historical information," "think," etc.
- Avoid any expressions that suggest the answer's origin is machine-generated or system-processed, such as "according to information provided by the knowledge graph," "the document chunk indicates," "experimental data shows (DC)," "the diagram illustrates through," etc.
- Remove the "References" section at the end of the answer, as well as all similar "[KG]" and "[DC]" citation markers within the text.

3. Use Natural Language Expression:
- Ensure sentences are coherent and logically clear, with natural transitions between paragraphs.
- If the original answer contains direct references or repetitions of "sub-questions" (e.g., "needs to be addressed"), integrate them into the overall narrative or present these points in a more natural way, avoiding the direct use of "sub_questions" or "sub-questions."

4. Retain Original Structure: 
- While removing system jargon, retain the original answer's structural elements as much as possible, such as headings, subheadings, lists, tables, formulas, and images, to maintain clarity and readability.

"""

PROMPTS[
    "similarity_check"
] = """Please analyze the similarity between these two questions:

Question 1: {original_prompt}
Question 2: {cached_prompt}

Please evaluate whether these two questions are semantically similar, and whether the answer to Question 2 can be used to answer Question 1, provide a similarity score between 0 and 1 directly.

Similarity score criteria:
0: Completely unrelated or answer cannot be reused, including but not limited to:
   - The questions have different topics
   - The locations mentioned in the questions are different
   - The times mentioned in the questions are different
   - The specific individuals mentioned in the questions are different
   - The specific events mentioned in the questions are different
   - The background information in the questions is different
   - The key conditions in the questions are different
1: Identical and answer can be directly reused
0.5: Partially related and answer needs modification to be used
Return only a number between 0-1, without any additional content.
"""
