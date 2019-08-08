$(function(){

  var n_images = $('img').filter(function() { 
      return this.id.match('image*');}).length

  var visible_idx = 0;

  if (n_images <= 1) {
      $(".image-btn").hide()
  }

  // click handlers for quiz buttons
  $(".quiz-option").on('click',function () {
    this.children[0].checked = true;
    $("#quizform").submit()
  });

  // handler to scroll through images
  $(".image-btn").on('click',function () {
    visible_idx++;
    hide_images(visible_idx % n_images);
  });

  function hide_images(idx) {
    var i;
    for (i = 0; i < n_images; i++) {
      $("#image_" + (i+1).toString()).hide()
    }
    $("#image_" + (idx+1).toString()).show()
  }

  // in the beginning, hide all but first
  hide_images(0)

}); 
