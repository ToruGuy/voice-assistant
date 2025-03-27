Streaming
Stream Chat Completions in real time. Receive chunks of completions returned from the model using server-sent events. Learn more.
The chat completion chunk object
Represents a streamed chunk of a chat completion response returned by the model, based on the provided input. Learn more.

choices
array
A list of chat completion choices. Can contain more than one elements if n is greater than 1. Can also be empty for the last chunk if you set stream_options: {"include_usage": true}.

Show properties
created
integer
The Unix timestamp (in seconds) of when the chat completion was created. Each chunk has the same timestamp.
id
string
A unique identifier for the chat completion. Each chunk has the same ID.
model
string
The model to generate the completion.
object
string
The object type, which is always chat.completion.chunk.
service_tier
string or null
The service tier used for processing the request.
system_fingerprint
string
This fingerprint represents the backend configuration that the model runs with. Can be used in conjunction with the seed request parameter to understand when backend changes have been made that might impact determinism.
usage
object or null
Usage statistics for the completion request.

Show properties
OBJECT The chat completion chunk object
{"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4o-mini", "system_fingerprint": "fp_44709d6fcb", "choices":[{"index":0,"delta":{"role":"assistant","content":""},"logprobs":null,"finish_reason":null}]}

{"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4o-mini", "system_fingerprint": "fp_44709d6fcb", "choices":[{"index":0,"delta":{"content":"Hello"},"logprobs":null,"finish_reason":null}]}

....

{"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4o-mini", "system_fingerprint": "fp_44709d6fcb", "choices":[{"index":0,"delta":{},"logprobs":null,"finish_reason":"stop"}]}