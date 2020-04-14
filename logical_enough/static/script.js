/* modifications of documents */
function documents_management_setup() {
    let $documents = $('#documents');
    $documents.attr('type', 'hidden');

    let document_txts = $documents.val().split(';');
    $documents.val('');

    let $table = $('<div id="tableInputDocuments"></div>');
    for (let i in document_txts) {
        documents_management_add_doc($table, document_txts[i], false);
    }

    let $tableDiv = $('<div></div>');
    $tableDiv.append($table);

    let $add_row_link = $('<a href="#">Ajouter une ligne</a>');
    $add_row_link.click(function () {
        documents_management_add_doc($table, '');
    });
    $tableDiv.append($('<p></p>').append($add_row_link));

    $tableDiv.insertAfter($documents);

    // add expr_hint and check fields
    let $hint_expr = $('#hint_expr');
    $hint_expr.keyup(function () {
        documents_management_change_expr($hint_expr);
    });

    documents_management_change_expr($hint_expr);
}

function documents_management_modify_doc(input) {
    // modify list
    let new_value = input.val();
    let previous_value = input.data('prev-value');
    let $documents = $('#documents');

    let document_txts = $documents.val().split(';');
    let index = document_txts.indexOf(previous_value);
    if (index > -1) {
        document_txts[index] = new_value;
    } else {
        document_txts.push(new_value);
    }
    $documents.val(document_txts.join(';'));
    input.data('prev-value', new_value);

    // check matching
    documents_management_doc_check_match(input);
}

function documents_management_doc_check_match(input) {
    $.ajax({
        url: '/api/checks',
        data: {
            document: input.val(),
            search_expression: $('#hint_expr').val()
        },
        success: function (result) {
            if ('matched' in result) {
                documents_management_set_matched(input, result['matched']);
            } else {
                documents_management_set_matched(input, false);
                console.log(result);
            }
        },
        error: function (xhr, status, error) {
            documents_management_set_matched(input, false);
            console.log(error);
        }

    });
}

function documents_management_set_matched(input, matched) {
     // input.css('border-color', matched ? 'green': 'red');
     input.css('background-color', matched ? '#cfc': '#fcc');
}

function documents_management_add_doc($table, txt, check=true) {
    let $inputText = $('<input type="text" class="inputDocument form-control" value="' + txt + '" />');
    $inputText.data('prev-value', txt);

    $inputText.keyup(function () {
        documents_management_modify_doc($(this));
    });

    let $tr = $('<div class="input-group"></div>').append($inputText);

    let $linkDel = $('<button class="btn btn-default" type="button"><span class="glyphicon glyphicon-remove" aria-hidden="true"></span></button>');
    $linkDel.click(function () {
        let val = $tr.find('.inputDocument').val();
        let $documents = $('#documents');
        let vals = $documents.val().split(';');
        let index = vals.indexOf(val);
        if (index > -1)
            vals.splice(index, 1);
        $documents.val(vals.join(';'));
        $tr.remove();
    });

    $tr.append($('<div class="input-group-btn"></div>').append($linkDel));

    $table.append($tr);

    let $documents = $('#documents');
    let v = $documents.val();
    if (v === '') {
        v = txt;
    } else {
        v = v + ';' + txt;
    }
    $documents.val(v);

    if (check)
        documents_management_doc_check_match($inputText);
}

function documents_management_change_expr(input) {
    let $documents = $('.inputDocument');
    let vals = [];

    $documents.each(function () {
        vals.push($(this).val());
    });

    $.ajax({
        url: '/api/checks_many',
        data: {
            documents: vals,
            search_expression: input.val()
        },
        traditional: true,
        success: function (result) {
            if ('matched' in result) {
                let matched = result['matched'];
                let i = 0;
                $documents.each(function () {
                    documents_management_set_matched($(this), matched[i]);
                    i += 1;
                })
            } else {
                console.log(result);
            }
        },
        error: function (xhr, status, error) {
            console.log(error);
        }

    });
}

/* challenge stuffs */
function challenge_setup(user, challenge, question) {
    let $search_expr = $('#search_expr');
    let $button = $('#search_button');

    $button.click(function () {
        challenge_test($search_expr, user, challenge, question);
    });

    // first time
    challenge_test($search_expr, user, challenge, question);
}

function challenge_test(input, user, challenge, question) {
    let $button = $('#search_button');
    $button.prop('disabled', true);

    $.ajax({
        url: '/api/check_question',
        method: 'POST',
        data: {
            search_expression: input.val(),
            user: user,
            challenge: challenge,
            question: question
        },
        success: function (result) {
            challenge_treat_result(result, challenge);
        },
        error: function (xhr, status, error) {
            console.log(error);
        }
    });

    $button.prop('disabled', false);
}

function challenge_treat_result(result) {
    let $goodDocs = $('#goodDocs');
    let $wrongDocs = $('#wrongDocs');

    $goodDocs.html('');
    $wrongDocs.html('');

    let gd = result['good_documents'];
    let wd = result['wrong_documents'];

    gd.forEach(function (a) {
         $goodDocs.append('<span class="doc-result doc-'+ a[1] +'">'+ a[0] +'</span>')
    });

    wd.forEach(function (a) {
         $wrongDocs.append('<span class="doc-result doc-'+ a[1] +'">'+ a[0] +'</span>')
    });

    if(result['question_end']) {
        $('#search_button').click(function () {
            console.log('we\'re good')
        });

        $('#search_expr').prop('disabled', true);
        $('#messageSucceed').css('display', 'block')
    }
}
