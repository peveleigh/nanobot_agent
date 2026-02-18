# Nanobot Conversation Agent

This custom component integrates a Nanobot conversation agent with Home Assistant, allowing you to use your Nanobot instance as a conversational AI backend.

## Features

*   **Empower Your Home Assistant with Nanobot Intelligence**: Seamlessly integrate your custom Nanobot conversation agent to handle voice commands and natural language interactions within Home Assistant.
*   **Real-time, Responsive Conversations**: Experience fluid interactions as user utterances are instantly forwarded to your Nanobot instance, and responses are delivered back to Home Assistant in real-time via a dedicated, secure webhook.
*   **Local Control & Privacy**: Leveraging Home Assistant's `local_push` IoT class, this integration prioritizes local communication where possible, enhancing privacy and responsiveness.

## Installation

### Manual Installation

1.  Download the latest release from the [GitHub repository](https://github.com/your-org/nanobot).
2.  Unpack the contents into your Home Assistant `custom_components` folder.
    Your `custom_components` folder should look like this:

    ```
    custom_components/
    └── nanobot_agent/
        ├── __init__.py
        ├── config_flow.py
        ├── const.py
        ├── conversation.py
        ├── manifest.json
        └── webhook.py
    ```
3.  Restart Home Assistant.

## Configuration

After installation, you can configure the Nanobot Conversation Agent through the Home Assistant UI:

1.  Go to **Settings** -> **Devices & Services**.
2.  Click on **+ ADD INTEGRATION**.
3.  Search for "Nanobot Conversation Agent".
4.  You will be prompted to enter the following information:
    *   **Nanobot URL**: The full URL of your running Nanobot service (e.g., `http://your-nanobot-host:18790/`). This is where Home Assistant will send user utterances.
    *   **Agent Name** (Optional): A friendly name for your Nanobot agent in Home Assistant (defaults to "Nanobot").
    *   **Request Timeout** (Optional): The maximum time (in seconds) Home Assistant will wait for a response from Nanobot (defaults to 30 seconds).

5.  Once configured, Home Assistant will register a webhook URL that your Nanobot service needs to use to send responses back to Home Assistant. This URL will be displayed during the configuration process or can be found in the integration's system logs. Ensure your Nanobot service is configured to send responses to this webhook.

## Usage

Once configured, you can interact with your Nanobot agent through Home Assistant's conversation features:

1.  Go to **Developer Tools** -> **Services**.
2.  Call the `conversation.process` service.
3.  In the `text` field, enter your query (e.g., "Turn on the living room lights").
4.  The response from your Nanobot agent will be displayed.

You can also set your Nanobot agent as the default conversation agent in Home Assistant settings.

## Troubleshooting

*   **"Nanobot is not connected" / "Nanobot service is not reachable"**:
    *   Verify that your Nanobot service is running and accessible from your Home Assistant instance at the configured **Nanobot URL**.
    *   Check your Home Assistant logs for more details.
*   **"Nanobot did not respond in time"**:
    *   Increase the **Request Timeout** in the integration's configuration.
    *   Check the performance of your Nanobot service.
    *   Ensure your Nanobot service is correctly sending responses to the Home Assistant webhook.
*   **No response from Nanobot**:
    *   Ensure your Nanobot service is correctly configured with the webhook URL provided by Home Assistant.
    *   Check the logs of both Home Assistant and your Nanobot service for any errors.



