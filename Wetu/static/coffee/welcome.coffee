sectionIndex = 0
nQuestions = 4
nSections = 6
sliderSize = 250
finished = false

validateEmail = (email)->
  re = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/
  return re.test(email)

loadLoginForm = ()->

	$('.cd-footer').hide()
	finished = true

	$.get( "accounts/login/", ( data )=>
		parser = new DOMParser()
		doc = parser.parseFromString(data.html, "text/html")

		$('#login-form').html( doc.getElementById('login_form') )
		
		$('#id_login').attr('placeholder', "Nom d'utilisateur ou email")
		$('#id_username').attr('placeholder', "Nom d'utilisateur")
		$('label[for="id_remember"]').text('se souvenir de moi').css({'margin-left': '10px'}).parent().css( { 'display': 'flex', 'flex-direction': 'row-reverse' } )

		localStorage.setItem('just-logged-in', 'true')
		localStorage.setItem('selected-edition', location.pathname)

		return
	)

	return true

surveyActions = {
	5: loadLoginForm
}

stateObject = {
	sectionIndex: sectionIndex
}

window.onpopstate = (event) ->
	console.log("location: " + document.location + ", state: " + JSON.stringify(event.state));
	sectionIndex = event.state.sectionIndex
	surveyActivateSection(false)
	return

surveyActivateSection = (pushState=true)->
	$('.section').hide()
	sectionNumber = sectionIndex+1
	$('.section-' + sectionNumber).removeClass('hidden').show()
	$('.cd-footer .progression').text(if sectionNumber <= nQuestions then sectionNumber + ' / ' + nQuestions else 'Terminé')
	$('.cd-footer .bar').css( width: Math.min(sliderSize, sectionNumber * sliderSize / nQuestions) )
	$('.cd-validate').hide()

	if pushState
		stateObject.sectionIndex = sectionIndex
		history.pushState(stateObject, "page " + sectionNumber)
	return

surveyNext = ()->
	if finished or sectionIndex >= (nSections - 1) then return
	sectionNumber = sectionIndex+1
	if surveyActions[sectionNumber]? and not surveyActions[sectionNumber]() then return
	sectionIndex++
	surveyActivateSection()
	return

surveyPrevious = ()->
	if finished or sectionIndex == 0 then return
	sectionIndex--
	surveyActivateSection()
	return

$(document).ready () ->
	justLoggedIn = localStorage.getItem('just-logged-in') == 'true'
	
	if justLoggedIn
		localStorage.removeItem('just-logged-in')

	if localStorage.getItem('selected-edition') != null && justLoggedIn && $('.editions').attr('data-authenticated') == 'True'
		window.location = localStorage.getItem('selected-edition')
		return

	buttons = $('.editions li').each (index, element)=>
		buttonHref = $(element).find('a').attr('href')
		$(element).click (e)=>
			localStorage.setItem('selected-edition', buttonHref)
			return

	$('#submit-form').click (event)->
		event.preventDefault()
		event.stopPropagation()
		$('#intro-video').empty()

		$('.participate-section').removeClass('hidden').show()
		$('form .cd-footer').removeClass('hidden').show()
		$('#submit-form').hide()
		surveyActivateSection()
		
		# $('input[type=radio]').change((event)->
		# 	if $(this).is(':checked')

		# )
		return -1

	$('.cd-radio').click (event)->
		event.preventDefault()
		event.stopPropagation()

		$('#intro-video').empty()
		$('form .cd-footer').removeClass('hidden').show()
		surveyActivateSection()

		$(this).addClass('checked').siblings('.cd-radio').removeClass('checked')

		if $(this).hasClass('validate')
			$('.cd-validate').removeClass('hidden').show()
		else
			setTimeout(surveyNext, 500)

		return -1

	$('.cd-radio select').click (event)->
		event.preventDefault()
		event.stopPropagation()
		return -1

	$('.cd-radio select').on('change', (event)->
		event.preventDefault()
		event.stopPropagation()

		$('.cd-radio').removeClass('checked')

		$(this).parents('.cd-radio').addClass('checked').siblings('.cd-radio').removeClass('checked')

		$('.cd-validate').removeClass('hidden').show()
		return -1)

	$('.cd-checkbox').click (event)->
		event.preventDefault()
		event.stopPropagation()
		$(this).toggleClass('checked')
		$('.cd-validate').removeClass('hidden').show()
		return -1

	$('.cd-validate button').click (event)->
		event.preventDefault()
		event.stopPropagation()
		surveyNext()
		return -1

	$('.cd-footer .btn.up').click (event)->
		event.preventDefault()
		event.stopPropagation()
		surveyPrevious()
		return -1

	$('.cd-footer .btn.down').click (event)->
		event.preventDefault()
		event.stopPropagation()
		surveyNext()
		return -1

	$('#id_email').on("change paste keyup", ()->
		text = $(this).val()
	
		if validateEmail(text)
			$('.cd-validate').removeClass('hidden').show()
		else
			$('.cd-validate').hide()
		return
	)

			
	return