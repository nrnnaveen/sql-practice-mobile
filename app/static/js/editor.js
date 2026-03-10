let editor;

require.config({ paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.44.0/min/vs" } });
require(["vs/editor/editor.main"], function () {
    editor = monaco.editor.create(document.getElementById("editor"), {
        value: "SELECT * FROM users;",
        language: "sql",
        theme: "vs-dark",
        automaticLayout: true
    });
});

function saveQuery() {
    document.getElementById("query").value = editor.getValue();
}

function loadQuery(q) {
    editor.setValue(q);
}
