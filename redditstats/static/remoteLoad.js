function remoteLoad() {
    $('.remote-load').each(function(i, value) {
        var element = $(value)
        element.load(element.data('url'))
    })
}
$(function() {
   remoteLoad()
})
